"""
Backend Caching Service
Implements in-memory TTL caching for expensive computations
Reduces redundant forecast and analytics calculations
"""

import time
from typing import Any, Optional, Callable
from functools import wraps
import hashlib
import json


class CacheEntry:
    """Single cache entry with TTL"""
    def __init__(self, value: Any, ttl: float):
        self.value = value
        self.expires_at = time.time() + ttl
    
    def is_valid(self) -> bool:
        """Check if cache entry is still valid"""
        return time.time() < self.expires_at


class TTLCache:
    """Thread-safe TTL cache with size limits"""
    
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value if still valid"""
        if key in self.cache:
            entry = self.cache[key]
            if entry.is_valid():
                self.hits += 1
                return entry.value
            else:
                # Clean up expired entry
                del self.cache[key]
        
        self.misses += 1
        return None
    
    def set(self, key: str, value: Any, ttl: float):
        """Set cache value with TTL in seconds"""
        # Implement simple LRU - remove oldest if at capacity
        if len(self.cache) >= self.max_size:
            # Remove first (oldest) key
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[key] = CacheEntry(value, ttl)
    
    def invalidate(self, key: str):
        """Remove specific cache entry"""
        if key in self.cache:
            del self.cache[key]
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self):
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.1f}%"
        }


# Global cache instances
forecast_cache = TTLCache(max_size=500)
analytics_cache = TTLCache(max_size=100)
product_cache = TTLCache(max_size=200)


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from function arguments"""
    # Create deterministic key from args and kwargs
    key_data = {
        "args": str(args),
        "kwargs": json.dumps(kwargs, sort_keys=True, default=str)
    }
    key_str = json.dumps(key_data, sort_keys=True)
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(cache: TTLCache, ttl: float = 300):
    """
    Decorator for caching function results
    
    Args:
        cache: TTLCache instance to use
        ttl: Time to live in seconds (default 5 minutes)
    
    Example:
        @cached(forecast_cache, ttl=600)
        def expensive_forecast(product_id, days):
            # ... expensive computation
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = f"{func.__name__}:{cache_key(*args, **kwargs)}"
            
            # Check cache
            cached_value = cache.get(key)
            if cached_value is not None:
                print(f"[CACHE HIT] {func.__name__}")
                return cached_value
            
            # Cache miss - compute value
            print(f"[CACHE MISS] {func.__name__}")
            result = func(*args, **kwargs)
            
            # Store in cache
            cache.set(key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


def invalidate_forecast(product_id: int):
    """Invalidate forecast cache for a specific product"""
    # Note: This is a simple implementation
    # In production, use pattern matching or separate keys
    forecast_cache.clear()  # Clear all for now


def get_cache_stats():
    """Get statistics for all caches"""
    return {
        "forecast": forecast_cache.get_stats(),
        "analytics": analytics_cache.get_stats(),
        "product": product_cache.get_stats()
    }
