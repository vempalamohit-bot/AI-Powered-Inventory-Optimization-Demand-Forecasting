/**
 * Frontend cache service for API responses
 * Stores data in memory to avoid refetching on tab switches
 */

class FrontendCache {
    constructor() {
        this.cache = new Map();
        this.timestamps = new Map();
    }

    /**
     * Get cached data if still fresh
     * @param {string} key - Cache key
     * @param {number} ttl - Time to live in seconds (default: 60s)
     * @returns {any|null} - Cached data or null if expired/missing
     */
    get(key, ttl = 60) {
        if (!this.cache.has(key)) {
            return null;
        }

        const timestamp = this.timestamps.get(key);
        const age = (Date.now() - timestamp) / 1000; // age in seconds

        if (age > ttl) {
            // Expired - remove it
            this.cache.delete(key);
            this.timestamps.delete(key);
            console.log(`⏰ Cache expired: ${key}`);
            return null;
        }

        console.log(`✅ Cache hit: ${key} (age: ${age.toFixed(1)}s)`);
        return this.cache.get(key);
    }

    /**
     * Set cache data
     * @param {string} key - Cache key
     * @param {any} data - Data to cache
     */
    set(key, data) {
        this.cache.set(key, data);
        this.timestamps.set(key, Date.now());
        console.log(`💾 Cached: ${key}`);
    }

    /**
     * Invalidate specific key or all keys matching pattern
     * @param {string} keyOrPattern - Key or pattern to invalidate
     */
    invalidate(keyOrPattern) {
        if (keyOrPattern.endsWith('*')) {
            // Pattern match - remove all keys starting with pattern
            const prefix = keyOrPattern.slice(0, -1);
            const keysToDelete = Array.from(this.cache.keys()).filter(k => k.startsWith(prefix));
            keysToDelete.forEach(k => {
                this.cache.delete(k);
                this.timestamps.delete(k);
            });
            console.log(`🗑️ Invalidated: ${keyOrPattern} (${keysToDelete.length} items)`);
        } else {
            // Exact key
            this.cache.delete(keyOrPattern);
            this.timestamps.delete(keyOrPattern);
            console.log(`🗑️ Invalidated: ${keyOrPattern}`);
        }
    }

    /**
     * Clear all cache
     */
    clear() {
        this.cache.clear();
        this.timestamps.clear();
        console.log('🗑️ Cache cleared');
    }

    /**
     * Get cache stats
     */
    stats() {
        return {
            size: this.cache.size,
            keys: Array.from(this.cache.keys())
        };
    }
}

// Export singleton instance
export const frontendCache = new FrontendCache();
