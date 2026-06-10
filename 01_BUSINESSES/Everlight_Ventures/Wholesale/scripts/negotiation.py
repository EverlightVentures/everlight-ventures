#!/usr/bin/env python3
"""
negotiation.py -- the SHARED negotiation engine. Used by BOTH the live auto_responder
(real seller/buyer replies) AND wholesale_sim_e2e (the dry-run). One brain for the math so
the simulation and real life behave identically.

Two sides, opposite directions:
  SELLER side  -- we want LOW. Open below our ceiling (max we will pay), concede UP across
                  rounds toward the ceiling, never past it. ceiling = MAO-derived agreed cap.
  BUYER  side  -- we want HIGH. Open at our ask (Chris all-in target), concede DOWN toward
                  our floor (ask minus give, never below assign that keeps min margin).

Each call returns the next number + whether to accept/hold/counter. The MESSAGE itself is
written by llm_compose with this number + the round context, so it sounds human and on-voice.
"""
from __future__ import annotations


def _round_k(n: int) -> int:
    return int(round(n / 500.0) * 500)


def seller_next(round_n: int, opening: int, ceiling: int, their_counter: int | None = None) -> dict:
    """We are BUYING from the seller. opening < ceiling (the most we will pay).
    Concede UP across rounds; accept if their counter is at/under ceiling."""
    if their_counter is not None and their_counter <= ceiling:
        return {"action": "accept", "offer": their_counter, "round": round_n,
                "rationale": f"their ask ${their_counter:,} is at or under our ceiling ${ceiling:,}"}
    ladder = {1: opening, 2: _round_k((opening + ceiling) / 2), 3: ceiling}
    offer = ladder.get(min(round_n, 3), ceiling)
    if their_counter is not None:
        # meet partway but never above ceiling
        offer = min(ceiling, _round_k((offer + min(their_counter, ceiling)) / 2))
    action = "counter" if offer < ceiling else ("final" if round_n >= 3 else "counter")
    return {"action": action, "offer": offer, "round": round_n, "ceiling": ceiling,
            "rationale": f"round {round_n}: offer ${offer:,} (walk-away ${ceiling:,})"}


def buyer_next(round_n: int, ask: int, floor: int, their_counter: int | None = None) -> dict:
    """We are SELLING (assigning) to the buyer. ask >= floor (lowest assignment that keeps
    our min margin). Concede DOWN toward floor; accept if their counter is at/above floor."""
    if their_counter is not None and their_counter >= floor:
        return {"action": "accept", "offer": their_counter, "round": round_n,
                "rationale": f"their ${their_counter:,} is at or above our floor ${floor:,}"}
    ladder = {1: ask, 2: _round_k((ask + floor) / 2), 3: floor}
    offer = ladder.get(min(round_n, 3), floor)
    if their_counter is not None:
        offer = max(floor, _round_k((offer + max(their_counter, floor)) / 2))
    action = "hold" if round_n == 1 else ("final" if offer <= floor else "counter")
    return {"action": action, "offer": offer, "round": round_n, "floor": floor,
            "rationale": f"round {round_n}: hold ${offer:,} (floor ${floor:,})"}


if __name__ == "__main__":
    print("SELLER (we buy, ceiling 17000, open 15000):")
    print(" ", seller_next(1, 15000, 17000))
    print(" ", seller_next(2, 15000, 17000, their_counter=20000))
    print(" ", seller_next(3, 15000, 17000, their_counter=17000))
    print("BUYER (we assign, ask 21000, floor 20000):")
    print(" ", buyer_next(1, 21000, 20000))
    print(" ", buyer_next(2, 21000, 20000, their_counter=19000))
