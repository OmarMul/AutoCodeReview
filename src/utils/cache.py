import time
import functools
from typing import Any, Optional, Callable, Dict
from collections import OrderedDict
from dataclasses import dataclass
from threading import Lock
from src.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0

    def __str__(self) -> str:
        return (f"CacheStats(hits={self.hits}, misses={self.misses}, "
                f"hit_rate={self.hit_rate:.2%}, size: {self.size}")

@dataclass
class CacheEntry:
    """single cashe entry with value and metadata"""
    value: Any
    created_at: float
    last_accessed: float
    ttl: Optional[float]

    def is_expired(self) -> bool:
        """check if entry is expired"""
        if self.ttl is None:
            return False
        return time.time() - self.last_accessed > self.ttl

    def access(self) -> Any:
        """Mark entry as accessed and return value"""
        self.last_accessed = time.time()
        return self.value


class Cache:
    """
    In-memory cache with TTL and LRU eviction.
    Thread-safe implementation.
    """
    def __init__(self, max_size: int = 1000, default_ttl: Optional[int] = None):
        
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._stats = CacheStats()

        logger.info(
            f"Initialized cache: max_size={max_size}, "
            f"default_ttl={default_ttl}s"
        )
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self._lock:
            if key not in self._cache:
                self._stats.misses += 1
                return None
            
            entry = self._cache[key]

            if entry.is_expired():
                logger.debug(f"Cache miss for key: {key} (expired)")
                del self._cache[key]
                self._stats.misses += 1
                self._stats.size = len(self._cache)
                return None
            self._cache.move_to_end(key)
            self._stats.hits += 1
            return entry.access()
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """set value in cache"""
        with self._lock:
            if ttl is None:
                ttl = self.default_ttl

            #create entry
            entry = CacheEntry(
                value=value,
                created_at=time.time(),
                last_accessed=time.time(),
                ttl=ttl
            )

            #check if it already exist
            if key in self._cache:
                self._cache[key] = entry
                self._cache.move_to_end(key)
            else:
                #add new entry
                self._cache[key] = entry

                #check size limit
                if len(self._cache) > self.max_size:
                    # Remove least recently used (first item)
                    evicated_key = next(iter(self._cache))
                    del self._cache[evicated_key]
                    self._stats.evictions += 1
                    logger.info(f"Cache evicted key (LRU): {evicated_key}")

            self._stats.size = len(self._cache)
            logger.debug(f"Added cache key: {key}")
    

    def delete(self, key: str) -> bool:
        """Delete entry from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.size = len(self._cache)
                logger.debug(f"Deleted cache key: {key}")
                return True
            return False
    
    def clear(self) -> None:
        """Clear the entire cache"""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.size = 0
            logger.info(f"Cache cleared: {count} items removed")
    
    def cleanup_expired(self) -> int:
        """Remove expired entries from cache"""
        with self._lock:
            expired_keys = [key for key, entry in self._cache.items()
                            if entry.is_expired()
                            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            self._stats.size = len(self._cache)

            if expired_keys:
                logger.info(f"Cache cleanup: removed {len(expired_keys)} expired entries")
            return len(expired_keys)
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            return CacheStats(
                hits=self._stats.hits,
                misses=self._stats.misses,
                evictions=self._stats.evictions,
                size=self._stats.size
            )
    def reset_stats(self) -> None:
        """Reset cache statistics."""
        with self._lock:
            self._stats = CacheStats(size=len(self._cache))
            logger.info("Cache statistics reset")

_llm_cache = Cache(max_size=500, default_ttl=3600)  # 1 hour
_parse_cache = Cache(max_size=1000, default_ttl=None)  # No expiration (invalidate by hash)
_analysis_cache = Cache(max_size=300, default_ttl=1800)  # 30 minutes


def get_llm_cache() -> Cache:
    """Get LLM response cache instance."""
    return _llm_cache


def get_parse_cache() -> Cache:
    """Get code parse result cache instance."""
    return _parse_cache


def get_analysis_cache() -> Cache:
    """Get analysis result cache instance."""
    return _analysis_cache

def cached(
    cache: Cache,
    key_func: Optional[Callable] = None,
    ttl: Optional[float] = None
):
    """
    Decorator to cache function results.
    
    Args:
        cache: Cache instance to use
        key_func: Function to generate cache key from args (default: str of args)
        ttl: Time-to-live override
    
    Example:
        @cached(get_llm_cache(), ttl=3600)
        def expensive_llm_call(prompt):
            return llm.generate(prompt)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default: use function name + str representation of args
                cache_key = f"{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Using cached result for {func.__name__}")
                return cached_value
            
            # Execute function
            logger.debug(f"Cache miss, executing {func.__name__}")
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        # Add cache management methods to wrapper
        wrapper.cache = cache
        wrapper.cache_clear = lambda: cache.clear()
        wrapper.cache_stats = lambda: cache.get_stats()
        
        return wrapper
    return decorator


def cache_by_hash(cache: Cache, ttl: Optional[float] = None):
    """
    Decorator to cache by content hash (for code parsing).
    Expects first argument to be the content string.
    
    Example:
        @cache_by_hash(get_parse_cache())
        def parse_code(code: str, language: str):
            return parser.parse(code)
    """
    def key_func(*args, **kwargs):
        from src.utils.file_handler import calculate_hash
        
        # First argument should be the content
        if args:
            content = args[0]
            content_hash = calculate_hash(content)
            # Include other args in key
            other_args = str(args[1:]) + str(kwargs)
            return f"hash:{content_hash}:{other_args}"
        return str(args) + str(kwargs)
    
    return cached(cache, key_func=key_func, ttl=ttl)


# Convenience decorators
def cache_llm_response(ttl: float = 3600):
    """Cache LLM responses (default 1 hour)."""
    return cached(get_llm_cache(), ttl=ttl)


def cache_parse_result():
    """Cache code parse results (by content hash, no expiration)."""
    return cache_by_hash(get_parse_cache())


def cache_analysis_result(ttl: float = 1800):
    """Cache analysis results (default 30 minutes)."""
    return cached(get_analysis_cache(), ttl=ttl)