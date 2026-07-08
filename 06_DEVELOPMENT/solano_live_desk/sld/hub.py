from __future__ import annotations

import asyncio

# In-process publish/subscribe hub for the live WebSocket push layer.
#
# One Hub instance (HUB) lives in the API process. Each connected /ws client
# owns one bounded asyncio.Queue registered via subscribe(). The broadcaster
# task calls publish(msg) and the message fans out to every queue without
# blocking: if a client is too slow and its queue is full, that client is
# dropped rather than stalling ingest or the other clients. Pure asyncio, no
# third-party dependency, no C extension. Nothing here can segfault.


class Hub:
    def __init__(self, maxq: int = 128) -> None:
        self._subs: set[asyncio.Queue] = set()
        self._maxq = maxq

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=self._maxq)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    def publish(self, msg: dict) -> int:
        """Fan msg out to all subscribers. Drop any whose queue is full
        (slow/dead client). Returns the number of live subscribers reached."""
        dead: list[asyncio.Queue] = []
        reached = 0
        for q in self._subs:
            try:
                q.put_nowait(msg)
                reached += 1
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self._subs.discard(q)
        return reached

    @property
    def count(self) -> int:
        return len(self._subs)


# Module-level singleton shared by the broadcaster and the /ws endpoint.
HUB = Hub()
