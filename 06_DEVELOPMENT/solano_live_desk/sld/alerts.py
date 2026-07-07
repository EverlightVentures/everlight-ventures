from __future__ import annotations

# routing[threat_level] -> list of (channel, ntfy_priority)
_ROUTING = {
    "EXTREME": [("push", 5), ("email", 0), ("dashboard", 0)],
    "HIGH": [("push", 4), ("email", 0), ("dashboard", 0)],
    "MEDIUM": [("digest", 0), ("dashboard", 0)],
    "LOW": [("dashboard", 0)],
    "LOG": [("dashboard", 0)],
}


def plan(threat_level: str) -> list[tuple[str, int]]:
    """Channels + push priority for a threat level."""
    return _ROUTING.get(threat_level, [("dashboard", 0)])


def dispatch(event: dict, senders: dict) -> list[dict]:
    """Fire an event through its routed channels.

    senders maps channel name -> callable(event, priority) -> truthy on success.
    A channel with no sender is skipped. A sender that raises is captured, never
    propagated, so one dead channel cannot silence the others (safety-critical).
    """
    receipts: list[dict] = []
    for channel, prio in plan(event.get("threat_level", "LOG")):
        fn = senders.get(channel)
        if fn is None:
            continue
        try:
            ok = fn(event, prio)
            receipts.append({"channel": channel, "priority": prio, "ok": bool(ok)})
        except Exception as e:  # noqa: BLE001 - never let one channel break the rest
            receipts.append({"channel": channel, "priority": prio, "ok": False, "error": str(e)})
    return receipts
