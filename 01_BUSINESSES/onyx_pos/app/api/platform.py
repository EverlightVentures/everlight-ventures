"""
Onyx Platform -- Consumer-Side Commerce Engine
The protocol layer for neighborhood commerce.

7 feature domains:
1. Customer Profiles + Loyalty Wallet
2. QR Receipts (physical-digital bridge)
3. Social Clout System
4. Sports Prediction Market
5. Fashion Drop Culture Engine
6. Voice Commerce / AI Agent Ordering
7. Predictive Commerce
"""
import hashlib
import json
import secrets
import string
from datetime import datetime, date, timedelta, timezone
from typing import Optional

from db import supabase


# ============================================================
# CUSTOMER PROFILES + LOYALTY WALLET
# ============================================================

TIER_THRESHOLDS = {
    "bronze": 0,
    "silver": 500,
    "gold": 2000,
    "platinum": 10000,
    "obsidian": 50000,
}


def _hash_phone(phone: str) -> str:
    """Hash a phone number for privacy-first identity."""
    cleaned = "".join(c for c in phone if c.isdigit())
    return hashlib.sha256(f"onyx:{cleaned}".encode()).hexdigest()


def _generate_referral_code() -> str:
    chars = string.ascii_uppercase + string.digits
    return f"ONYX-{''.join(secrets.choice(chars) for _ in range(6))}"


def _compute_tier(lifetime_points: int) -> str:
    tier = "bronze"
    for t, threshold in sorted(TIER_THRESHOLDS.items(), key=lambda x: x[1], reverse=True):
        if lifetime_points >= threshold:
            return t
    return tier


def get_or_create_customer(phone: str, display_name: str = None) -> dict:
    """Get existing customer or create new one by phone number."""
    phone_hash = _hash_phone(phone)

    existing = supabase.table("onyx_customers").select("*").eq(
        "phone_hash", phone_hash
    ).execute()

    if existing.data:
        return existing.data[0]

    # Create new customer
    customer = supabase.table("onyx_customers").insert({
        "phone_hash": phone_hash,
        "display_name": display_name or f"Onyx Member",
        "referral_code": _generate_referral_code(),
    }).execute()

    return customer.data[0]


def earn_points(customer_id: str, points: int, reason: str,
                tenant_id: str = None, reference_id: str = None) -> dict:
    """Add loyalty points to a customer's wallet."""
    customer = supabase.table("onyx_customers").select(
        "loyalty_points, lifetime_points"
    ).eq("id", customer_id).single().execute()

    new_balance = customer.data["loyalty_points"] + points
    new_lifetime = customer.data["lifetime_points"] + points
    new_tier = _compute_tier(new_lifetime)

    # Update customer
    supabase.table("onyx_customers").update({
        "loyalty_points": new_balance,
        "lifetime_points": new_lifetime,
        "tier": new_tier,
    }).eq("id", customer_id).execute()

    # Record in ledger
    supabase.table("onyx_points_ledger").insert({
        "customer_id": customer_id,
        "tenant_id": tenant_id,
        "points": points,
        "balance_after": new_balance,
        "reason": reason,
        "reference_id": reference_id,
    }).execute()

    return {"points_earned": points, "balance": new_balance, "tier": new_tier}


def spend_points(customer_id: str, points: int, reason: str,
                 tenant_id: str = None, reference_id: str = None) -> dict:
    """Spend loyalty points from a customer's wallet."""
    customer = supabase.table("onyx_customers").select(
        "loyalty_points"
    ).eq("id", customer_id).single().execute()

    if customer.data["loyalty_points"] < points:
        return {"error": f"Insufficient points. Balance: {customer.data['loyalty_points']}"}

    new_balance = customer.data["loyalty_points"] - points

    supabase.table("onyx_customers").update({
        "loyalty_points": new_balance,
    }).eq("id", customer_id).execute()

    supabase.table("onyx_points_ledger").insert({
        "customer_id": customer_id,
        "tenant_id": tenant_id,
        "points": -points,
        "balance_after": new_balance,
        "reason": reason,
        "reference_id": reference_id,
    }).execute()

    return {"points_spent": points, "balance": new_balance}


def record_visit(customer_id: str, tenant_id: str, transaction_id: str,
                 items: list, total: float) -> dict:
    """Record a customer visit and update streaks."""
    today = date.today()

    # Record visit
    supabase.table("onyx_customer_visits").insert({
        "customer_id": customer_id,
        "tenant_id": tenant_id,
        "transaction_id": transaction_id,
        "items_purchased": json.dumps(items),
        "total_spent": total,
        "visit_day": today.strftime("%A"),
        "visit_hour": datetime.now().hour,
    }).execute()

    # Update streak
    customer = supabase.table("onyx_customers").select(
        "current_streak, longest_streak, last_visit_date, total_visits, total_spent, loyalty_points, lifetime_points"
    ).eq("id", customer_id).single().execute()

    c = customer.data
    last_visit = date.fromisoformat(c["last_visit_date"]) if c.get("last_visit_date") else None

    if last_visit == today:
        new_streak = c["current_streak"]  # Same day, no change
    elif last_visit == today - timedelta(days=1):
        new_streak = c["current_streak"] + 1  # Consecutive day
    else:
        new_streak = 1  # Streak broken, restart

    longest = max(new_streak, c.get("longest_streak", 0))

    # Points: 1 point per dollar spent + streak bonus
    base_points = int(total)
    streak_bonus = min(new_streak * 2, 50)  # Max 50 bonus points for streaks
    total_points = base_points + streak_bonus

    new_loyalty = c["loyalty_points"] + total_points
    new_lifetime = c["lifetime_points"] + total_points

    supabase.table("onyx_customers").update({
        "current_streak": new_streak,
        "longest_streak": longest,
        "last_visit_date": today.isoformat(),
        "total_visits": c["total_visits"] + 1,
        "total_spent": float(c["total_spent"]) + total,
        "loyalty_points": new_loyalty,
        "lifetime_points": new_lifetime,
        "tier": _compute_tier(new_lifetime),
    }).eq("id", customer_id).execute()

    # Record in ledger
    supabase.table("onyx_points_ledger").insert({
        "customer_id": customer_id,
        "tenant_id": tenant_id,
        "points": total_points,
        "balance_after": new_loyalty,
        "reason": f"purchase ({base_points}pts) + streak_bonus ({streak_bonus}pts)",
        "reference_id": transaction_id,
    }).execute()

    result = {
        "points_earned": total_points,
        "streak": new_streak,
        "balance": new_loyalty,
        "tier": _compute_tier(new_lifetime),
    }

    # Streak milestone alerts
    if new_streak in [7, 14, 30, 50, 100, 365]:
        result["milestone"] = f"{new_streak}-day streak! Bonus {new_streak * 5} points!"
        earn_points(customer_id, new_streak * 5, f"streak_milestone_{new_streak}", tenant_id)

    return result


# ============================================================
# QR RECEIPTS
# ============================================================

def generate_qr_receipt(tenant_id: str, transaction_id: str,
                        customer_id: str = None,
                        lottery_code_id: str = None,
                        cross_promo_id: str = None) -> dict:
    """Generate a QR code payload for a receipt.

    The QR encodes a JSON payload with:
    - Transaction summary
    - Lottery code (if generated)
    - Cross-promo code (if available)
    - Social share link
    """
    short_code = secrets.token_urlsafe(6)

    payload = {
        "v": 1,  # payload version
        "tx": transaction_id[:8],  # short tx ref
        "t": tenant_id[:8],
        "ts": datetime.now(timezone.utc).isoformat()[:19],
    }

    if lottery_code_id:
        payload["lottery"] = lottery_code_id[:8]
    if cross_promo_id:
        payload["promo"] = cross_promo_id[:8]

    record = supabase.table("onyx_qr_receipts").insert({
        "tenant_id": tenant_id,
        "transaction_id": transaction_id,
        "customer_id": customer_id,
        "qr_code_data": json.dumps(payload),
        "short_url": f"onyx.link/{short_code}",
        "lottery_code_id": lottery_code_id,
        "cross_promo_id": cross_promo_id,
    }).execute()

    return {
        "qr_id": record.data[0]["id"],
        "short_url": f"onyx.link/{short_code}",
        "payload": payload,
    }


# ============================================================
# SOCIAL CLOUT SYSTEM
# ============================================================

CLOUT_REWARDS = {
    "purchase_share": 10,
    "lottery_win": 25,
    "streak_milestone": 15,
    "level_up": 20,
    "review": 30,
    "photo": 15,
    "drop_cop": 50,
    "prediction_win": 20,
}


def create_social_post(customer_id: str, post_type: str,
                       tenant_id: str = None, content_text: str = None,
                       reference_id: str = None, platforms: list = None) -> dict:
    """Create a social sharing post and earn clout points."""
    clout = CLOUT_REWARDS.get(post_type, 5)

    post = supabase.table("onyx_social_posts").insert({
        "customer_id": customer_id,
        "tenant_id": tenant_id,
        "post_type": post_type,
        "content_text": content_text,
        "platforms": platforms or [],
        "clout_points_earned": clout,
        "reference_id": reference_id,
    }).execute()

    # Award clout points as loyalty points
    earn_points(customer_id, clout, "social_share", tenant_id, post.data[0]["id"])

    # Update social score
    supabase.rpc("increment_social_score", {
        "cid": customer_id, "pts": clout
    }).execute() if False else supabase.table("onyx_customers").update({
        "social_score": supabase.table("onyx_customers").select("social_score").eq(
            "id", customer_id).single().execute().data.get("social_score", 0) + clout
    }).eq("id", customer_id).execute()

    return {
        "post_id": post.data[0]["id"],
        "clout_earned": clout,
        "message": f"Earned {clout} clout points for sharing!",
    }


def get_leaderboard(tenant_id: str = None, board_type: str = "spending",
                    period: str = "weekly") -> list:
    """Get leaderboard rankings."""
    existing = supabase.table("onyx_leaderboards").select("rankings").eq(
        "board_type", board_type
    ).eq("period", period).order("computed_at", desc=True).limit(1).execute()

    if existing.data:
        rankings = existing.data[0].get("rankings", [])
        if isinstance(rankings, str):
            rankings = json.loads(rankings)
        return rankings

    return []


# ============================================================
# SPORTS PREDICTION MARKET
# ============================================================

def create_prediction_event(title: str, category: str, options: list,
                            locks_at: str, event_time: str = None,
                            tenant_id: str = None) -> dict:
    """Create a prediction event for customers to bet on."""
    event = supabase.table("onyx_prediction_events").insert({
        "tenant_id": tenant_id,
        "title": title,
        "category": category,
        "options": json.dumps(options),
        "locks_at": locks_at,
        "event_time": event_time,
    }).execute()

    return event.data[0]


def place_prediction_bet(customer_id: str, event_id: str,
                         option_id: str, points_wagered: int) -> dict:
    """Place a prediction bet using loyalty points."""
    # Check event is open
    event = supabase.table("onyx_prediction_events").select("*").eq(
        "id", event_id
    ).single().execute()

    if not event.data:
        return {"error": "Event not found"}
    if event.data["status"] != "open":
        return {"error": "Betting is closed for this event"}

    # Check customer has enough points
    result = spend_points(customer_id, points_wagered, "prediction_bet", reference_id=event_id)
    if "error" in result:
        return result

    # Find odds for selected option
    options = event.data["options"]
    if isinstance(options, str):
        options = json.loads(options)
    odds = 2.0  # default
    for opt in options:
        if opt["id"] == option_id:
            odds = float(opt.get("odds", 2.0))
            break

    bet = supabase.table("onyx_prediction_bets").insert({
        "event_id": event_id,
        "customer_id": customer_id,
        "option_id": option_id,
        "points_wagered": points_wagered,
        "odds_at_time": odds,
    }).execute()

    # Update total wagered
    supabase.table("onyx_prediction_events").update({
        "total_points_wagered": event.data.get("total_points_wagered", 0) + points_wagered,
    }).eq("id", event_id).execute()

    potential_win = int(points_wagered * odds)

    return {
        "bet_id": bet.data[0]["id"],
        "option": option_id,
        "wagered": points_wagered,
        "odds": odds,
        "potential_win": potential_win,
        "message": f"Bet placed! {points_wagered} points on {option_id} at {odds}x odds. Potential win: {potential_win} points.",
    }


def resolve_prediction(event_id: str, correct_option_id: str) -> dict:
    """Resolve a prediction event and pay out winners."""
    supabase.table("onyx_prediction_events").update({
        "status": "resolved",
        "correct_option_id": correct_option_id,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", event_id).execute()

    # Find all bets
    bets = supabase.table("onyx_prediction_bets").select("*").eq(
        "event_id", event_id
    ).execute()

    winners = 0
    total_payout = 0

    for bet in bets.data:
        won = bet["option_id"] == correct_option_id
        payout = int(bet["points_wagered"] * float(bet["odds_at_time"])) if won else 0

        supabase.table("onyx_prediction_bets").update({
            "won": won,
            "points_won": payout,
        }).eq("id", bet["id"]).execute()

        if won:
            earn_points(bet["customer_id"], payout, "prediction_win", reference_id=event_id)
            winners += 1
            total_payout += payout

    return {
        "resolved": True,
        "correct_option": correct_option_id,
        "total_bets": len(bets.data),
        "winners": winners,
        "total_payout": total_payout,
    }


# ============================================================
# FASHION DROP CULTURE ENGINE
# ============================================================

def create_drop(tenant_id: str, title: str, products: list,
                drop_time: str, drop_type: str = "fcfs",
                max_per_customer: int = 1,
                collab_tenant_id: str = None) -> dict:
    """Create a product drop event."""
    total_inventory = sum(p.get("quantity", 0) for p in products)

    drop = supabase.table("onyx_drops").insert({
        "tenant_id": tenant_id,
        "title": title,
        "products": json.dumps(products),
        "drop_time": drop_time,
        "drop_type": drop_type,
        "max_per_customer": max_per_customer,
        "total_inventory": total_inventory,
        "remaining_inventory": total_inventory,
        "collab_tenant_id": collab_tenant_id,
    }).execute()

    return drop.data[0]


def join_waitlist(drop_id: str, customer_id: str, bid_amount: int = None) -> dict:
    """Join the waitlist for a drop."""
    # Check if already on waitlist
    existing = supabase.table("onyx_drop_waitlist").select("id").eq(
        "drop_id", drop_id
    ).eq("customer_id", customer_id).execute()

    if existing.data:
        return {"error": "Already on the waitlist"}

    # Get customer tier for raffle bonus
    customer = supabase.table("onyx_customers").select("tier").eq(
        "id", customer_id
    ).single().execute()

    tier_bonus = {"bronze": 1, "silver": 2, "gold": 3, "platinum": 5, "obsidian": 10}
    raffle_entries = tier_bonus.get(customer.data.get("tier", "bronze"), 1)

    # Get current waitlist count for position
    count = supabase.table("onyx_drop_waitlist").select("id", count="exact").eq(
        "drop_id", drop_id
    ).execute()

    entry = supabase.table("onyx_drop_waitlist").insert({
        "drop_id": drop_id,
        "customer_id": customer_id,
        "position": (count.count or 0) + 1,
        "raffle_entries": raffle_entries,
        "bid_amount": bid_amount,
    }).execute()

    # Increment waitlist count on drop
    drop = supabase.table("onyx_drops").select("waitlist_count").eq(
        "id", drop_id
    ).single().execute()
    supabase.table("onyx_drops").update({
        "waitlist_count": (drop.data.get("waitlist_count", 0) or 0) + 1,
    }).eq("id", drop_id).execute()

    return {
        "waitlist_id": entry.data[0]["id"],
        "position": (count.count or 0) + 1,
        "raffle_entries": raffle_entries,
        "message": f"You're #{(count.count or 0) + 1} on the waitlist! ({raffle_entries}x raffle entries for your {customer.data.get('tier', 'bronze')} tier)",
    }


# ============================================================
# VOICE COMMERCE / AI AGENT ORDERING
# ============================================================

def create_voice_order(customer_id: str, channel: str,
                       message: str, tenant_id: str = None) -> dict:
    """Start a voice/text commerce order.

    The AI agent parses the natural language order into structured items.
    """
    order = supabase.table("onyx_voice_orders").insert({
        "customer_id": customer_id,
        "tenant_id": tenant_id,
        "channel": channel,
        "conversation": json.dumps([
            {"role": "user", "content": message, "timestamp": datetime.now(timezone.utc).isoformat()}
        ]),
        "status": "pending",
    }).execute()

    return {
        "order_id": order.data[0]["id"],
        "status": "pending",
        "message": "Order received! An AI agent is processing your request. You'll get a confirmation shortly.",
    }


# ============================================================
# PREDICTIVE COMMERCE
# ============================================================

def predict_customer_order(customer_id: str, tenant_id: str) -> dict:
    """Predict what a customer will order based on their history.

    Analyzes: visit patterns (day/time), purchase frequency,
    seasonal trends, most common items.
    """
    # Get last 90 days of visits at this merchant
    since = (datetime.utcnow() - timedelta(days=90)).isoformat()
    visits = supabase.table("onyx_customer_visits").select(
        "items_purchased, total_spent, visit_day, visit_hour"
    ).eq("customer_id", customer_id).eq("tenant_id", tenant_id).gte(
        "created_at", since
    ).execute()

    if not visits.data or len(visits.data) < 3:
        return {"prediction": None, "message": "Not enough purchase history for prediction"}

    # Aggregate items
    item_counts = {}
    time_patterns = {}
    day_patterns = {}

    for visit in visits.data:
        items = visit.get("items_purchased", [])
        if isinstance(items, str):
            items = json.loads(items)

        hour = visit.get("visit_hour", 12)
        day = visit.get("visit_day", "Unknown")

        for item in items:
            name = item.get("name", "Unknown")
            qty = item.get("qty", 1)
            item_counts[name] = item_counts.get(name, 0) + qty

            # Track when they buy this item
            key = f"{name}|{day}|{hour}"
            time_patterns[key] = time_patterns.get(key, 0) + 1

        day_patterns[day] = day_patterns.get(day, 0) + 1

    # Find most common items
    total_visits = len(visits.data)
    predicted_items = []

    for name, count in sorted(item_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        probability = round(count / total_visits, 2)
        if probability >= 0.3:  # Only predict items ordered 30%+ of the time
            predicted_items.append({
                "product_name": name,
                "probability": probability,
                "times_ordered": count,
            })

    if not predicted_items:
        return {"prediction": None, "message": "No strong purchase patterns detected yet"}

    confidence = round(sum(p["probability"] for p in predicted_items) / len(predicted_items), 2)

    # Save prediction
    now = datetime.now()
    prediction = supabase.table("onyx_customer_predictions").insert({
        "customer_id": customer_id,
        "tenant_id": tenant_id,
        "predicted_items": json.dumps(predicted_items),
        "prediction_confidence": confidence,
        "trigger_type": "time_pattern",
        "trigger_data": json.dumps({
            "day": now.strftime("%A"),
            "hour": now.hour,
            "total_visits": total_visits,
        }),
        "valid_for_date": date.today().isoformat(),
    }).execute()

    return {
        "prediction_id": prediction.data[0]["id"],
        "predicted_items": predicted_items,
        "confidence": confidence,
        "message": f"Based on {total_visits} visits, we predict this customer's usual order.",
        "suggested_greeting": f"Welcome back! The usual? ({', '.join(p['product_name'] for p in predicted_items[:3])})",
    }
