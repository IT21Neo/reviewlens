"""Small in-memory limiter for the endpoints that call the LLM proxy (/api/analyze, /api/ask).

Two limits, both configurable with environment variables:
  LIVE_PER_MINUTE  (default 5)    calls per client IP in any 60-second window
  LIVE_PER_DAY     (default 300)  calls for the whole app per UTC day (protects the course quota)
  LIVE_LLM_ENABLED (default 1)    set to 0 to switch live calls off entirely (cached data still works)

In-memory means the counters reset when the server restarts and are not shared between
processes; that is enough for a single-instance class demo, and it is documented as a limitation.
"""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone


class RateLimiter:
    def __init__(self, per_minute: int | None = None, per_day: int | None = None, enabled: bool | None = None,
                 clock=time.time):
        self.per_minute = per_minute if per_minute is not None else int(os.environ.get("LIVE_PER_MINUTE", 5))
        self.per_day = per_day if per_day is not None else int(os.environ.get("LIVE_PER_DAY", 300))
        self.enabled = enabled if enabled is not None else os.environ.get("LIVE_LLM_ENABLED", "1") != "0"
        self._clock = clock
        self._hits: dict[str, deque] = defaultdict(deque)
        self._day, self._day_count = "", 0
        self._lock = threading.Lock()

    def check(self, client: str) -> str | None:
        """Record one call. Returns None if allowed, otherwise a reason string."""
        if not self.enabled:
            return "live LLM calls are switched off on this server; cached results are still available"
        now = self._clock()
        today = datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m-%d")
        with self._lock:
            if today != self._day:
                self._day, self._day_count = today, 0
            if self._day_count >= self.per_day:
                return f"daily limit of {self.per_day} live calls reached; try again tomorrow"
            q = self._hits[client]
            while q and now - q[0] >= 60:
                q.popleft()
            if len(q) >= self.per_minute:
                return f"limit of {self.per_minute} live calls per minute reached; wait a moment"
            q.append(now)
            self._day_count += 1
        return None

    def status(self) -> dict:
        return {"enabled": self.enabled, "per_minute": self.per_minute, "per_day": self.per_day,
                "used_today": self._day_count}
