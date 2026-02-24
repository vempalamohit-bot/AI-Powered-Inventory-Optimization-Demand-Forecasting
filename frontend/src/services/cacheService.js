/**
 * Frontend Caching Service
 * Implements intelligent caching with TTL, invalidation, and lazy loading
 * Significantly improves performance by reducing redundant API calls
 */

class CacheService {
    constructor() {
        this.cache = new Map();
        this.timestamps = new Map();
        this.defaultTTL = 5 * 60 * 1000; // 5 minutes default
        this.maxSize = 100; // Max cache entries
    }

    /**
     * Generate cache key from endpoint and params
     */
    generateKey(endpoint, params = {}) {
        const paramStr = Object.keys(params)
            .sort()
            .map(k => `${k}=${JSON.stringify(params[k])}`)
            .join('&');
        return `${endpoint}${paramStr ? '?' + paramStr : ''}`;
    }

    /**
     * Get cached data if valid
     */
    get(key, ttl = this.defaultTTL) {
        if (!this.cache.has(key)) {
            return null;
        }

        const timestamp = this.timestamps.get(key);
        const now = Date.now();

        // Check if cache is still valid
        if (now - timestamp > ttl) {
            this.cache.delete(key);
            this.timestamps.delete(key);
            return null;
        }

        return this.cache.get(key);
    }

    /**
     * Set cache data
     */
    set(key, data) {
        // Implement LRU cache - remove oldest if at capacity
        if (this.cache.size >= this.maxSize) {
            const oldestKey = this.timestamps.keys().next().value;
            this.cache.delete(oldestKey);
            this.timestamps.delete(oldestKey);
        }

        this.cache.set(key, data);
        this.timestamps.set(key, Date.now());
    }

    /**
     * Invalidate specific cache entry
     */
    invalidate(key) {
        this.cache.delete(key);
        this.timestamps.delete(key);
    }

    /**
     * Invalidate by pattern (e.g., all forecast caches)
     */
    invalidatePattern(pattern) {
        const regex = new RegExp(pattern);
        const keysToDelete = [];

        for (const key of this.cache.keys()) {
            if (regex.test(key)) {
                keysToDelete.push(key);
            }
        }

        keysToDelete.forEach(key => {
            this.cache.delete(key);
            this.timestamps.delete(key);
        });

        return keysToDelete.length;
    }

    /**
     * Clear all cache
     */
    clear() {
        this.cache.clear();
        this.timestamps.clear();
    }

    /**
     * Get cache stats
     */
    getStats() {
        return {
            size: this.cache.size,
            maxSize: this.maxSize,
            entries: Array.from(this.cache.keys()),
            ages: Array.from(this.timestamps.entries()).map(([key, timestamp]) => ({
                key,
                age: Math.floor((Date.now() - timestamp) / 1000) + 's'
            }))
        };
    }
}

// Create singleton instance
export const cacheService = new CacheService();

/**
 * Cached API call wrapper
 * Automatically handles caching for API requests
 */
export async function cachedApiCall(
    apiFunction,
    cacheKey,
    options = {}
) {
    const {
        ttl = 5 * 60 * 1000, // 5 minutes default
        forceRefresh = false,
        onStale = null // Callback when returning stale data while refreshing
    } = options;

    // Check cache first (unless force refresh)
    if (!forceRefresh) {
        const cached = cacheService.get(cacheKey, ttl);
        if (cached) {
            console.log(`[Cache HIT] ${cacheKey}`);
            return cached;
        }
    }

    console.log(`[Cache MISS] ${cacheKey}`);

    try {
        // Make API call
        const response = await apiFunction();
        
        // Cache the response
        cacheService.set(cacheKey, response);
        
        return response;
    } catch (error) {
        // On error, return stale cache if available
        const stale = cacheService.get(cacheKey, Infinity);
        if (stale) {
            console.warn(`[Cache STALE] Returning stale data for ${cacheKey}`, error);
            if (onStale) onStale();
            return stale;
        }
        throw error;
    }
}

/**
 * Lazy loading helper
 * Loads data only when needed and caches the result
 */
export class LazyLoader {
    constructor(loaderFunction, cacheKey, options = {}) {
        this.loaderFunction = loaderFunction;
        this.cacheKey = cacheKey;
        this.options = options;
        this.loading = false;
        this.data = null;
        this.error = null;
    }

    async load(forceRefresh = false) {
        // Return cached data if available
        if (!forceRefresh && this.data) {
            return this.data;
        }

        // Prevent duplicate loads
        if (this.loading) {
            return null;
        }

        this.loading = true;
        this.error = null;

        try {
            this.data = await cachedApiCall(
                this.loaderFunction,
                this.cacheKey,
                { ...this.options, forceRefresh }
            );
            return this.data;
        } catch (err) {
            this.error = err;
            throw err;
        } finally {
            this.loading = false;
        }
    }

    reset() {
        this.data = null;
        this.error = null;
        this.loading = false;
        cacheService.invalidate(this.cacheKey);
    }
}

export default cacheService;
