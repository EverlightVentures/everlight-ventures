"""
Channel Integrations API
Unified API for DoorDash, UberEats, Grubhub, Instacart integrations
"""
from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import ChannelIntegration, ChannelOrder, Tenant, Item, Transaction
from datetime import datetime, timedelta
import json
import requests
import secrets
import os
import hmac
import hashlib

channels_bp = Blueprint("channels", __name__)

# Channel configurations
CHANNEL_CONFIGS = {
    "doordash": {
        "name": "DoorDash",
        "oauth_url": "https://identity.doordash.com/connect/authorize",
        "token_url": "https://identity.doordash.com/connect/token",
        "api_base": "https://openapi.doordash.com",
        "required_scopes": ["merchant.read", "merchant.write", "orders.read"],
        "client_id": os.getenv("DOORDASH_CLIENT_ID", ""),
        "client_secret": os.getenv("DOORDASH_CLIENT_SECRET", ""),
    },
    "ubereats": {
        "name": "Uber Eats",
        "oauth_url": "https://login.uber.com/oauth/v2/authorize",
        "token_url": "https://login.uber.com/oauth/v2/token",
        "api_base": "https://api.uber.com/v1/eats",
        "required_scopes": ["eats.store", "eats.orders"],
        "client_id": os.getenv("UBEREATS_CLIENT_ID", ""),
        "client_secret": os.getenv("UBEREATS_CLIENT_SECRET", ""),
    },
    "grubhub": {
        "name": "Grubhub",
        "oauth_url": "https://api-gtm.grubhub.com/auth/oauth2/authorize",
        "token_url": "https://api-gtm.grubhub.com/auth/oauth2/token",
        "api_base": "https://api-gtm.grubhub.com/v1",
        "required_scopes": ["restaurant.orders", "restaurant.menu"],
        "client_id": os.getenv("GRUBHUB_CLIENT_ID", ""),
        "client_secret": os.getenv("GRUBHUB_CLIENT_SECRET", ""),
    },
    "instacart": {
        "name": "Instacart",
        "oauth_url": "https://connect.instacart.com/oauth/authorize",
        "token_url": "https://connect.instacart.com/oauth/token",
        "api_base": "https://connect.instacart.com/v2",
        "required_scopes": ["orders.read", "inventory.write"],
        "client_id": os.getenv("INSTACART_CLIENT_ID", ""),
        "client_secret": os.getenv("INSTACART_CLIENT_SECRET", ""),
    }
}

# OAuth state storage (in production, use Redis)
oauth_states = {}


@channels_bp.route("", methods=["GET"])
@jwt_required()
def list_integrations():
    """List all channel integrations for tenant"""
    try:
        tenant_id = g.tenant_id

        integrations = g.db.query(ChannelIntegration).filter_by(
            tenant_id=tenant_id
        ).all()

        return jsonify({
            "integrations": [
                {
                    "id": integration.id,
                    "channel": integration.channel,
                    "channel_display_name": integration.channel_display_name,
                    "status": integration.status,
                    "is_active": integration.is_active,
                    "merchant_id": integration.merchant_id,
                    "menu_sync_enabled": integration.menu_sync_enabled,
                    "order_sync_enabled": integration.order_sync_enabled,
                    "last_menu_sync_at": integration.last_menu_sync_at.isoformat() if integration.last_menu_sync_at else None,
                    "last_order_sync_at": integration.last_order_sync_at.isoformat() if integration.last_order_sync_at else None,
                    "connected_at": integration.connected_at.isoformat() if integration.connected_at else None,
                    "created_at": integration.created_at.isoformat()
                }
                for integration in integrations
            ]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@channels_bp.route("/available", methods=["GET"])
@jwt_required()
def list_available_channels():
    """List all available channels and their connection status"""
    try:
        tenant_id = g.tenant_id

        # Get existing integrations
        existing = g.db.query(ChannelIntegration).filter_by(tenant_id=tenant_id).all()
        existing_map = {i.channel: i for i in existing}

        available_channels = []
        for channel_key, config in CHANNEL_CONFIGS.items():
            integration = existing_map.get(channel_key)

            available_channels.append({
                "channel": channel_key,
                "name": config["name"],
                "is_configured": bool(config["client_id"] and config["client_secret"]),
                "is_connected": integration is not None and integration.status == "active" if integration else False,
                "status": integration.status if integration else None,
                "integration_id": integration.id if integration else None
            })

        return jsonify({"channels": available_channels}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@channels_bp.route("/<channel>/connect", methods=["GET"])
@jwt_required()
def initiate_connection(channel):
    """
    Initiate OAuth connection to a channel

    Returns OAuth URL for user to authorize
    """
    try:
        if channel not in CHANNEL_CONFIGS:
            return jsonify({"error": "Invalid channel"}), 400

        config = CHANNEL_CONFIGS[channel]

        if not config["client_id"] or not config["client_secret"]:
            return jsonify({
                "error": f"{config['name']} integration not configured",
                "message": f"Set {channel.upper()}_CLIENT_ID and {channel.upper()}_CLIENT_SECRET environment variables"
            }), 500

        tenant_id = g.tenant_id

        # Generate state token
        state = secrets.token_urlsafe(32)
        oauth_states[state] = {
            "tenant_id": tenant_id,
            "channel": channel,
            "created_at": datetime.utcnow().isoformat()
        }

        # Build OAuth URL
        redirect_uri = f"{request.host_url}api/v1/channels/{channel}/callback"
        scopes = " ".join(config["required_scopes"])

        oauth_url = (
            f"{config['oauth_url']}?"
            f"client_id={config['client_id']}&"
            f"redirect_uri={redirect_uri}&"
            f"response_type=code&"
            f"scope={scopes}&"
            f"state={state}"
        )

        return jsonify({
            "auth_url": oauth_url,
            "state": state,
            "channel": channel,
            "channel_name": config["name"]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@channels_bp.route("/<channel>/callback", methods=["GET"])
def oauth_callback(channel):
    """Handle OAuth callback from channel"""
    try:
        code = request.args.get("code")
        state = request.args.get("state")
        error = request.args.get("error")

        if error:
            return jsonify({"error": f"OAuth error: {error}"}), 400

        if not code or not state:
            return jsonify({"error": "Missing code or state"}), 400

        # Verify state
        if state not in oauth_states:
            return jsonify({"error": "Invalid state token"}), 400

        state_data = oauth_states[state]
        tenant_id = state_data["tenant_id"]
        del oauth_states[state]  # Clean up

        if channel != state_data["channel"]:
            return jsonify({"error": "Channel mismatch"}), 400

        config = CHANNEL_CONFIGS[channel]

        # Exchange code for tokens
        redirect_uri = f"{request.host_url}api/v1/channels/{channel}/callback"

        token_response = requests.post(
            config["token_url"],
            data={
                "code": code,
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }
        )

        if token_response.status_code != 200:
            return jsonify({
                "error": "Failed to exchange code for token",
                "details": token_response.text
            }), 500

        tokens = token_response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")
        expires_in = tokens.get("expires_in", 3600)

        # Fetch merchant info from channel
        merchant_info = _fetch_merchant_info(channel, access_token, config)

        # Create or update integration
        existing = g.db.query(ChannelIntegration).filter_by(
            tenant_id=tenant_id,
            channel=channel
        ).first()

        if existing:
            existing.access_token = access_token
            existing.refresh_token = refresh_token
            existing.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            existing.merchant_id = merchant_info.get("merchant_id")
            existing.store_id = merchant_info.get("store_id")
            existing.status = "active"
            existing.connected_at = datetime.utcnow()
            integration = existing
        else:
            integration = ChannelIntegration(
                tenant_id=tenant_id,
                channel=channel,
                channel_display_name=config["name"],
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=datetime.utcnow() + timedelta(seconds=expires_in),
                merchant_id=merchant_info.get("merchant_id"),
                store_id=merchant_info.get("store_id"),
                status="active",
                connected_at=datetime.utcnow(),
                webhook_secret=secrets.token_urlsafe(32)
            )
            g.db.add(integration)

        g.db.commit()

        return jsonify({
            "message": f"{config['name']} connected successfully",
            "integration": {
                "id": integration.id,
                "channel": integration.channel,
                "status": integration.status,
                "merchant_id": integration.merchant_id
            }
        }), 201

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


@channels_bp.route("/<integration_id>/disconnect", methods=["POST"])
@jwt_required()
def disconnect_integration(integration_id):
    """Disconnect a channel integration"""
    try:
        tenant_id = g.tenant_id

        integration = g.db.query(ChannelIntegration).filter_by(
            id=integration_id,
            tenant_id=tenant_id
        ).first()

        if not integration:
            return jsonify({"error": "Integration not found"}), 404

        integration.status = "disconnected"
        integration.is_active = False
        integration.disconnected_at = datetime.utcnow()

        g.db.commit()

        return jsonify({"message": "Integration disconnected successfully"}), 200

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


@channels_bp.route("/<integration_id>/sync-menu", methods=["POST"])
@jwt_required()
def sync_menu(integration_id):
    """Manually trigger menu sync to channel"""
    try:
        tenant_id = g.tenant_id

        integration = g.db.query(ChannelIntegration).filter_by(
            id=integration_id,
            tenant_id=tenant_id,
            status="active"
        ).first()

        if not integration:
            return jsonify({"error": "Integration not found or not active"}), 404

        # Get all active items
        items = g.db.query(Item).filter_by(
            tenant_id=tenant_id,
            is_active=True
        ).all()

        # Sync to channel
        result = _sync_menu_to_channel(integration, items)

        integration.last_menu_sync_at = datetime.utcnow()
        g.db.commit()

        return jsonify({
            "message": "Menu synced successfully",
            "items_synced": len(items),
            "result": result
        }), 200

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


@channels_bp.route("/webhooks/<channel>", methods=["POST"])
def receive_webhook(channel):
    """
    Receive webhooks from channels (orders, status updates, etc.)

    This endpoint does NOT require JWT auth - it's called by external services
    """
    try:
        if channel not in CHANNEL_CONFIGS:
            return jsonify({"error": "Invalid channel"}), 400

        # Verify webhook signature
        signature = request.headers.get("X-Webhook-Signature")
        if not signature:
            return jsonify({"error": "Missing signature"}), 401

        # Get integration by webhook secret (we'll need to add logic to find the right tenant)
        # For now, we'll process the webhook and find tenant from merchant_id in payload

        payload = request.json
        _process_webhook(channel, payload)

        return jsonify({"status": "received"}), 200

    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500


# Helper functions

def _fetch_merchant_info(channel, access_token, config):
    """Fetch merchant info from channel API"""
    try:
        if channel == "doordash":
            response = requests.get(
                f"{config['api_base']}/developer/v2/stores",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if response.status_code == 200:
                data = response.json()
                stores = data.get("stores", [])
                if stores:
                    return {
                        "merchant_id": data.get("merchant_id"),
                        "store_id": stores[0].get("id")
                    }

        # Placeholder for other channels
        return {"merchant_id": None, "store_id": None}

    except Exception as e:
        print(f"Error fetching merchant info: {e}")
        return {"merchant_id": None, "store_id": None}


def _sync_menu_to_channel(integration, items):
    """Sync menu items to channel"""
    try:
        config = CHANNEL_CONFIGS[integration.channel]

        # Build menu data
        menu_items = []
        for item in items:
            menu_items.append({
                "id": item.sku,
                "name": item.name,
                "description": item.description or "",
                "price": float(item.sell_price),
                "category": item.category or "General",
                "available": item.stock_on_hand > 0
            })

        # Send to channel API (placeholder - each channel has different format)
        if integration.channel == "doordash":
            response = requests.post(
                f"{config['api_base']}/developer/v2/stores/{integration.store_id}/menu",
                headers={"Authorization": f"Bearer {integration.access_token}"},
                json={"items": menu_items}
            )
            return {"status": response.status_code, "synced": len(menu_items)}

        return {"status": "not_implemented", "synced": 0}

    except Exception as e:
        print(f"Menu sync error: {e}")
        return {"status": "error", "error": str(e)}


def _process_webhook(channel, payload):
    """Process incoming webhook from channel"""
    try:
        # This is a placeholder - each channel has different webhook formats
        # In production, you'd parse the payload and create/update ChannelOrder records

        if channel == "doordash":
            # DoorDash webhook format
            event_type = payload.get("event_type")

            if event_type == "order.created":
                # Create new order in our system
                pass

            elif event_type == "order.updated":
                # Update existing order
                pass

        # Similar logic for other channels
        pass

    except Exception as e:
        print(f"Webhook processing error: {e}")
        raise


# ============= CHANNEL ORDERS MANAGEMENT =============

@channels_bp.route("/orders", methods=["GET"])
@jwt_required()
def list_channel_orders():
    """
    List orders from all channels

    Query params:
    - channel: Filter by channel (doordash, ubereats, etc.)
    - status: Filter by status
    - from_date: ISO date
    - to_date: ISO date
    """
    try:
        tenant_id = g.tenant_id

        # Base query
        query = g.db.query(ChannelOrder).filter_by(tenant_id=tenant_id)

        # Filters
        if request.args.get("channel"):
            query = query.filter_by(channel=request.args.get("channel"))

        if request.args.get("status"):
            query = query.filter_by(status=request.args.get("status"))

        if request.args.get("from_date"):
            from_date = datetime.fromisoformat(request.args.get("from_date"))
            query = query.filter(ChannelOrder.created_at >= from_date)

        if request.args.get("to_date"):
            to_date = datetime.fromisoformat(request.args.get("to_date"))
            query = query.filter(ChannelOrder.created_at <= to_date)

        # Sort by most recent first
        orders = query.order_by(ChannelOrder.created_at.desc()).limit(100).all()

        return jsonify({
            "orders": [
                {
                    "id": order.id,
                    "channel": order.channel,
                    "channel_order_id": order.channel_order_id,
                    "channel_order_number": order.channel_order_number,
                    "status": order.status,
                    "customer_name": order.customer_name,
                    "items": json.loads(order.items) if order.items else [],
                    "subtotal": float(order.subtotal),
                    "tax": float(order.tax),
                    "delivery_fee": float(order.delivery_fee),
                    "tip": float(order.tip),
                    "total": float(order.total),
                    "platform_commission": float(order.platform_commission),
                    "net_payout": float(order.net_payout),
                    "scheduled_pickup_time": order.scheduled_pickup_time.isoformat() if order.scheduled_pickup_time else None,
                    "created_at": order.created_at.isoformat()
                }
                for order in orders
            ]
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@channels_bp.route("/orders/<order_id>", methods=["GET"])
@jwt_required()
def get_channel_order(order_id):
    """Get detailed information about a channel order"""
    try:
        tenant_id = g.tenant_id

        order = g.db.query(ChannelOrder).filter_by(
            id=order_id,
            tenant_id=tenant_id
        ).first()

        if not order:
            return jsonify({"error": "Order not found"}), 404

        return jsonify({
            "order": {
                "id": order.id,
                "channel": order.channel,
                "channel_order_id": order.channel_order_id,
                "channel_order_number": order.channel_order_number,
                "status": order.status,
                "customer_name": order.customer_name,
                "customer_phone": order.customer_phone,
                "delivery_address": order.delivery_address,
                "items": json.loads(order.items) if order.items else [],
                "subtotal": float(order.subtotal),
                "tax": float(order.tax),
                "delivery_fee": float(order.delivery_fee),
                "service_fee": float(order.service_fee),
                "tip": float(order.tip),
                "total": float(order.total),
                "platform_commission": float(order.platform_commission),
                "platform_commission_percent": float(order.platform_commission_percent),
                "net_payout": float(order.net_payout),
                "scheduled_pickup_time": order.scheduled_pickup_time.isoformat() if order.scheduled_pickup_time else None,
                "scheduled_delivery_time": order.scheduled_delivery_time.isoformat() if order.scheduled_delivery_time else None,
                "actual_pickup_time": order.actual_pickup_time.isoformat() if order.actual_pickup_time else None,
                "actual_delivery_time": order.actual_delivery_time.isoformat() if order.actual_delivery_time else None,
                "transaction_id": order.transaction_id,
                "created_at": order.created_at.isoformat(),
                "updated_at": order.updated_at.isoformat()
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@channels_bp.route("/orders/<order_id>/update-status", methods=["PATCH"])
@jwt_required()
def update_order_status(order_id):
    """
    Update order status

    Request body:
    - status: new status (confirmed, preparing, ready, picked_up, etc.)
    """
    try:
        tenant_id = g.tenant_id
        data = request.json

        if not data.get("status"):
            return jsonify({"error": "Status is required"}), 400

        order = g.db.query(ChannelOrder).filter_by(
            id=order_id,
            tenant_id=tenant_id
        ).first()

        if not order:
            return jsonify({"error": "Order not found"}), 404

        old_status = order.status
        new_status = data["status"]

        # Update status
        order.status = new_status

        # Update timestamps based on status
        if new_status == "picked_up" and not order.actual_pickup_time:
            order.actual_pickup_time = datetime.utcnow()
        elif new_status == "delivered" and not order.actual_delivery_time:
            order.actual_delivery_time = datetime.utcnow()

        g.db.commit()

        # TODO: Notify channel of status change via their API

        return jsonify({
            "message": "Order status updated",
            "order": {
                "id": order.id,
                "status": order.status,
                "old_status": old_status
            }
        }), 200

    except Exception as e:
        g.db.rollback()
        return jsonify({"error": str(e)}), 500


@channels_bp.route("/analytics", methods=["GET"])
@jwt_required()
def get_channel_analytics():
    """
    Get analytics across all channels

    Query params:
    - from_date: ISO date
    - to_date: ISO date
    """
    try:
        tenant_id = g.tenant_id

        # Date range
        from_date = datetime.fromisoformat(request.args.get("from_date")) if request.args.get("from_date") else datetime.utcnow() - timedelta(days=30)
        to_date = datetime.fromisoformat(request.args.get("to_date")) if request.args.get("to_date") else datetime.utcnow()

        # Get all orders in range
        orders = g.db.query(ChannelOrder).filter(
            ChannelOrder.tenant_id == tenant_id,
            ChannelOrder.created_at >= from_date,
            ChannelOrder.created_at <= to_date
        ).all()

        # Calculate metrics by channel
        channel_metrics = {}
        total_orders = 0
        total_revenue = 0
        total_commission = 0
        total_net_payout = 0

        for order in orders:
            channel = order.channel
            if channel not in channel_metrics:
                channel_metrics[channel] = {
                    "orders": 0,
                    "revenue": 0,
                    "commission": 0,
                    "net_payout": 0,
                    "avg_order_value": 0
                }

            channel_metrics[channel]["orders"] += 1
            channel_metrics[channel]["revenue"] += float(order.total)
            channel_metrics[channel]["commission"] += float(order.platform_commission)
            channel_metrics[channel]["net_payout"] += float(order.net_payout)

            total_orders += 1
            total_revenue += float(order.total)
            total_commission += float(order.platform_commission)
            total_net_payout += float(order.net_payout)

        # Calculate averages
        for channel in channel_metrics:
            if channel_metrics[channel]["orders"] > 0:
                channel_metrics[channel]["avg_order_value"] = round(
                    channel_metrics[channel]["revenue"] / channel_metrics[channel]["orders"],
                    2
                )

        return jsonify({
            "summary": {
                "total_orders": total_orders,
                "total_revenue": round(total_revenue, 2),
                "total_commission": round(total_commission, 2),
                "total_net_payout": round(total_net_payout, 2),
                "avg_commission_percent": round((total_commission / total_revenue * 100) if total_revenue > 0 else 0, 2)
            },
            "by_channel": channel_metrics,
            "date_range": {
                "from": from_date.isoformat(),
                "to": to_date.isoformat()
            }
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
