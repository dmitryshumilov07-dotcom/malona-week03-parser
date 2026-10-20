from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    """Simple in-memory limiter: N requests / 60s per key + pause per supplier."""

    def __init__(self, per_min: int, supplier_pause_sec: float, max_parallel: int):
        self.per_min = per_min
        self.supplier_pause_sec = supplier_pause_sec
        self.max_parallel = max_parallel
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._last_supplier: dict[str, float] = {}
        self._inflight: dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

    def check_key(self, api_key: str) -> tuple[bool, int]:
        now = time.time()
        with self._lock:
            q = self._hits[api_key]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= self.per_min:
                retry_after = max(1, int(60 - (now - q[0])) + 1)
                return False, retry_after
            q.append(now)
            return True, 0

    def acquire_supplier(self, supplier_id: str) -> tuple[bool, float]:
        with self._lock:
            if self._inflight[supplier_id] >= self.max_parallel:
                return False, 1.0
            last = self._last_supplier.get(supplier_id, 0.0)
            wait = self.supplier_pause_sec - (time.time() - last)
            if wait > 0:
                return False, wait
            self._inflight[supplier_id] += 1
            self._last_supplier[supplier_id] = time.time()
            return True, 0.0

    def release_supplier(self, supplier_id: str) -> None:
        with self._lock:
            self._inflight[supplier_id] = max(0, self._inflight[supplier_id] - 1)
