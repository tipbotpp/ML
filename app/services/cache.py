import hashlib
import sys
from typing import Any, Optional, TypeVar, Generic
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import OrderedDict

from app.services.logger import get_logger

logger = get_logger().bind(layer="service", module="cache")

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    value: T
    created_at: datetime
    ttl_seconds: Optional[int] = None
    access_count: int = 0
    last_accessed: datetime = None

    def __post_init__(self):
        if self.last_accessed is None:
            self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        if self.ttl_seconds is None:
            return False
        elapsed = (datetime.now() - self.created_at).total_seconds()
        return elapsed > self.ttl_seconds

    def get_size_bytes(self) -> int:
        try:
            return sys.getsizeof(self.value)
        except:
            return 0


class CacheManager:
    def __init__(
        self,
        default_ttl_seconds: Optional[int] = None,
        max_entries: Optional[int] = 1000,
        max_memory_mb: Optional[float] = None,
    ):
        self._cache: dict[str, CacheEntry[Any]] = {}
        self._default_ttl_seconds = default_ttl_seconds
        self._max_entries = max_entries
        self._max_memory_mb = max_memory_mb
        self._access_order: OrderedDict = OrderedDict()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "max_size_reached": 0,
        }

    def generate_key(self, *parts: str) -> str:
        combined = ":".join(str(p) for p in parts)
        return hashlib.sha256(combined.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        if key not in self._cache:
            self._stats["misses"] += 1
            logger.debug("cache.miss", key=key[:16])
            return None

        entry = self._cache[key]
        if entry.is_expired():
            self._stats["misses"] += 1
            logger.debug("cache.expired", key=key[:16])
            del self._cache[key]
            self._access_order.pop(key, None)
            return None

        entry.access_count += 1
        entry.last_accessed = datetime.now()
        self._access_order.move_to_end(key)
        self._stats["hits"] += 1
        logger.debug("cache.hit", key=key[:16], access_count=entry.access_count)
        return entry.value

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        effective_ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl_seconds
        entry = CacheEntry(
            value=value,
            created_at=datetime.now(),
            ttl_seconds=effective_ttl,
        )

        entry_size = entry.get_size_bytes()

        self._ensure_capacity(key, entry_size)

        self._cache[key] = entry
        self._access_order[key] = True
        self._access_order.move_to_end(key)
        self._stats["sets"] += 1

        logger.debug("cache.set", key=key[:16], ttl_seconds=effective_ttl, size_bytes=entry_size)
        return True

    def _ensure_capacity(self, new_key: str, new_entry_size: int) -> None:
        if self._max_entries and len(self._cache) >= self._max_entries:
            if new_key not in self._cache:
                self._evict_lru()
                self._stats["max_size_reached"] += 1

        if self._max_memory_mb:
            total_size = sum(e.get_size_bytes() for e in self._cache.values())
            total_size += new_entry_size
            max_bytes = self._max_memory_mb * 1024 * 1024

            while total_size > max_bytes and self._cache:
                evicted_size = self._evict_lru()
                total_size -= evicted_size

    def _evict_lru(self) -> int:
        if not self._access_order:
            return 0

        lru_key = next(iter(self._access_order))
        evicted_entry = self._cache.pop(lru_key)
        self._access_order.pop(lru_key)
        self._stats["evictions"] += 1

        evicted_size = evicted_entry.get_size_bytes()
        logger.debug("cache.evict_lru", key=lru_key[:16], size_bytes=evicted_size)
        return evicted_size

    def clear(self, prefix: Optional[str] = None) -> int:
        if prefix is None:
            count = len(self._cache)
            self._cache.clear()
            self._access_order.clear()
            logger.info("cache.cleared_all", count=count)
            return count
        else:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(prefix)]
            for k in keys_to_delete:
                del self._cache[k]
                self._access_order.pop(k, None)
            logger.info("cache.cleared_prefix", prefix=prefix, count=len(keys_to_delete))
            return len(keys_to_delete)

    def cleanup_expired(self) -> int:
        expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
        for k in expired_keys:
            del self._cache[k]
            self._access_order.pop(k, None)
        if expired_keys:
            logger.info("cache.cleanup_expired", removed=len(expired_keys))
        return len(expired_keys)

    def get_stats(self) -> dict[str, Any]:
        self.cleanup_expired()

        total_entries = len(self._cache)
        expired_entries = sum(1 for e in self._cache.values() if e.is_expired())
        active_entries = total_entries - expired_entries

        total_size = sum(e.get_size_bytes() for e in self._cache.values())
        hit_rate = (
            self._stats["hits"] / (self._stats["hits"] + self._stats["misses"])
            if (self._stats["hits"] + self._stats["misses"]) > 0
            else 0
        )

        avg_accesses = (
            sum(e.access_count for e in self._cache.values()) / active_entries
            if active_entries > 0
            else 0
        )

        return {
            "total_entries": total_entries,
            "active_entries": active_entries,
            "expired_entries": expired_entries,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "hit_rate": round(hit_rate, 4),
            "total_hits": self._stats["hits"],
            "total_misses": self._stats["misses"],
            "total_sets": self._stats["sets"],
            "total_evictions": self._stats["evictions"],
            "max_size_reached_count": self._stats["max_size_reached"],
            "avg_accesses_per_entry": round(avg_accesses, 2),
            "max_entries": self._max_entries,
            "max_memory_mb": self._max_memory_mb,
        }
