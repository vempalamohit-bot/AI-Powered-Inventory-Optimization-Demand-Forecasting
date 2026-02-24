"""
Simple in-memory cache for API responses with TTL (Time To Live)
"""
from datetime import datetime, timedelta
from typing import Any, Optional
import hashlib
import json

class SimpleCache:
    def __init__(self):
        self._cache = {}
    
    def _make_key(self, endpoint: str, params: dict) -> str:
        """Create cache key from endpoint and params"""
        param_str = json.dumps(params, sort_keys=True)
        return f"{endpoint}:{hashlib.md5(param_str.encode()).hexdigest()}"
    
    def get(self, endpoint: str, params: dict = None) -> Optional[Any]:
        """Get cached value if not expired"""
        params = params or {}
        key = self._make_key(endpoint, params)
        
        if key in self._cache:
            value, expiry = self._cache[key]
            if datetime.now() < expiry:
                print(f"✅ Cache HIT: {endpoint}")
                return value
            else:
                # Expired - remove it
                del self._cache[key]
                print(f"⏰ Cache EXPIRED: {endpoint}")
        
        print(f"❌ Cache MISS: {endpoint}")
        return None
    
    def set(self, endpoint: str, value: Any, ttl_seconds: int = 60, params: dict = None):
        """Set cache value with TTL"""
        params = params or {}
        key = self._make_key(endpoint, params)
        expiry = datetime.now() + timedelta(seconds=ttl_seconds)
        self._cache[key] = (value, expiry)
        print(f"💾 Cache SET: {endpoint} (TTL: {ttl_seconds}s)")
    
    def invalidate(self, endpoint: str = None):
        """Clear cache for specific endpoint or all"""
        if endpoint:
            # Clear all keys starting with endpoint
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(endpoint + ":")]
            for key in keys_to_remove:
                del self._cache[key]
            print(f"🗑️  Cache INVALIDATED: {endpoint}")
        else:
            self._cache.clear()
            print("🗑️  Cache CLEARED (all)")
    
    def size(self) -> int:
        """Get number of cached items"""
        return len(self._cache)

# Global cache instance
api_cache = SimpleCache()
