"""
Tests for caching utilities.
"""

import time
import pytest
from src.utils.cache import Cache, cached, cache_by_hash


class TestCache:
    """Test basic cache functionality."""
    
    def test_cache_set_get(self):
        """Test basic set and get operations."""
        cache = Cache(max_size=100)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
    
    def test_cache_miss(self):
        """Test cache miss returns None."""
        cache = Cache(max_size=100)
        
        assert cache.get("nonexistent") is None
    
    def test_cache_ttl_expiration(self):
        """Test TTL expiration."""
        cache = Cache(max_size=100, default_ttl=0.1)  # 100ms TTL
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(0.2)
        
        assert cache.get("key1") is None
    
    def test_cache_lru_eviction(self):
        """Test LRU eviction when max size exceeded."""
        cache = Cache(max_size=3)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # All should be present
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        
        # Add 4th item - should evict key1 (least recently used)
        cache.set("key4", "value4")
        
        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_cache_lru_with_access(self):
        """Test LRU considers recent access."""
        cache = Cache(max_size=3)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        
        # Access key1 to make it recently used
        cache.get("key1")
        
        # Add 4th item - should evict key2 (now least recently used)
        cache.set("key4", "value4")
        
        assert cache.get("key1") == "value1"  # Still present
        assert cache.get("key2") is None      # Evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
    
    def test_cache_delete(self):
        """Test deleting cache entries."""
        cache = Cache(max_size=100)
        
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        
        assert cache.delete("nonexistent") is False
    
    def test_cache_clear(self):
        """Test clearing all cache entries."""
        cache = Cache(max_size=100)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        stats = cache.get_stats()
        assert stats.size == 0
    
    def test_cache_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = Cache(max_size=100, default_ttl=0.1)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2", ttl=10)  # Won't expire
        
        time.sleep(0.2)
        
        removed = cache.cleanup_expired()
        
        assert removed == 1
        assert cache.get("key1") is None  # Expired
        assert cache.get("key2") == "value2"  # Still valid
    
    def test_cache_stats(self):
        """Test cache statistics tracking."""
        cache = Cache(max_size=100)
        
        # Set some values
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Hit
        cache.get("key1")
        
        # Miss
        cache.get("key3")
        
        stats = cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.size == 2
        assert 0 < stats.hit_rate < 1
    
    def test_cache_override_ttl(self):
        """Test overriding default TTL."""
        cache = Cache(max_size=100, default_ttl=10)
        
        # Override with shorter TTL
        cache.set("key1", "value1", ttl=0.1)
        
        time.sleep(0.2)
        
        assert cache.get("key1") is None


class TestCachedDecorator:
    """Test cached decorator."""
    
    def test_cached_decorator_basic(self):
        """Test basic caching decorator."""
        cache = Cache(max_size=100)
        call_count = 0
        
        @cached(cache)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call - executes function
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1
        
        # Second call - uses cache
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # Not called again
        
        # Different argument - executes function
        result3 = expensive_function(10)
        assert result3 == 20
        assert call_count == 2
    
    def test_cached_decorator_custom_key(self):
        """Test cached decorator with custom key function."""
        cache = Cache(max_size=100)
        
        def key_func(x, y):
            return f"sum:{x+y}"
        
        @cached(cache, key_func=key_func)
        def add(x, y):
            return x + y
        
        result1 = add(2, 3)
        result2 = add(1, 4)  # Different args, same sum
        
        # Should use cache because key_func returns same key
        stats = cache.get_stats()
        assert stats.hits == 1


class TestCacheByHash:
    """Test cache_by_hash decorator."""
    
    def test_cache_by_content_hash(self):
        """Test caching by content hash."""
        cache = Cache(max_size=100)
        call_count = 0
        
        @cache_by_hash(cache)
        def parse_code(code, language):
            nonlocal call_count
            call_count += 1
            return f"Parsed {language}: {code}"
        
        code1 = "def hello(): pass"
        
        # First call
        result1 = parse_code(code1, "python")
        assert call_count == 1
        
        # Same code - should use cache
        result2 = parse_code(code1, "python")
        assert call_count == 1  # Cache hit
        
        # Different code - new parse
        code2 = "def goodbye(): pass"
        result3 = parse_code(code2, "python")
        assert call_count == 2


class TestGlobalCaches:
    """Test global cache instances."""
    
    def test_llm_cache_instance(self):
        """Test LLM cache exists and has correct settings."""
        from src.utils.cache import get_llm_cache
        
        cache = get_llm_cache()
        assert cache.max_size == 500
        assert cache.default_ttl == 3600
    
    def test_parse_cache_instance(self):
        """Test parse cache exists and has correct settings."""
        from src.utils.cache import get_parse_cache
        
        cache = get_parse_cache()
        assert cache.max_size == 1000
        assert cache.default_ttl is None  # No expiration
    
    def test_analysis_cache_instance(self):
        """Test analysis cache exists and has correct settings."""
        from src.utils.cache import get_analysis_cache
        
        cache = get_analysis_cache()
        assert cache.max_size == 300
        assert cache.default_ttl == 1800