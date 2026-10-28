"""
cache_service.py - Simple in-process TTL cache.
Avoids hammering external APIs (AQI, weather, KSNDMC, etc.) on every request.
Usage:
    cache = TTLCache(ttl_seconds=300)
    data = await cache.get_or_fetch("key", async_fetcher_fn)
"""
import time
import asyncio
from typing import Any, Callable, Awaitable


class TTLCache:
    def __init__(self, ttl_seconds: int = 300):
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[Any, float]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _is_fresh(self, key: str) -> bool:
        if key not in self._store:
            return False
        _, ts = self._store[key]
        return (time.monotonic() - ts) < self._ttl

    def get(self, key: str) -> Any | None:
        if self._is_fresh(key):
            return self._store[key][0]
        return None

    def set(self, key: str, value: Any) -> None:
        self._store[key] = (value, time.monotonic())

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    async def get_or_fetch(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[Any]],
    ) -> Any:
        """Return cached value or call fetcher() to populate it."""
        cached = self.get(key)
        if cached is not None:
            return cached

        # Prevent stampede: one fetch per key at a time
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        async with self._locks[key]:
            # Re-check after acquiring lock
            cached = self.get(key)
            if cached is not None:
                return cached
            value = await fetcher()
            self.set(key, value)
            return value


# Shared cache instances with different TTLs
aqi_cache     = TTLCache(ttl_seconds=300)   # 5 min
weather_cache = TTLCache(ttl_seconds=600)   # 10 min
rainfall_cache = TTLCache(ttl_seconds=180)  # 3 min
noise_cache   = TTLCache(ttl_seconds=900)   # 15 min
traffic_cache = TTLCache(ttl_seconds=120)   # 2 min
