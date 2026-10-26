from __future__ import annotations

import time
from collections import defaultdict, deque


class SlidingWindowLimiter:
    """Small in-process limiter. Good enough for a single landing container."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        events = self._events[key]
        cutoff = now - self.window

        while events and events[0] <= cutoff:
            events.popleft()

        if len(events) >= self.limit:
            return False

        events.append(now)
        if len(self._events) > 10_000:
            self._prune(cutoff)
        return True

    def _prune(self, cutoff: float) -> None:
        for key in list(self._events):
            events = self._events[key]
            if not events or events[-1] <= cutoff:
                del self._events[key]
