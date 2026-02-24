/**
 * Refresh Service - Handles data synchronization across all tabs and pages
 * When data is uploaded or restocked, this service notifies all components to refresh
 */

const REFRESH_EVENT = 'inventory-data-refresh';
const STORAGE_KEY = 'inventory-last-update';

/**
 * Trigger a data refresh event across the application
 * @param {string} source - The source of the refresh (e.g., 'upload', 'restock', 'sales')
 */
export const triggerRefresh = (source = 'unknown') => {
    const timestamp = Date.now();
    
    // Dispatch custom event for same-tab communication
    window.dispatchEvent(new CustomEvent(REFRESH_EVENT, {
        detail: { source, timestamp }
    }));
    
    // Update localStorage for cross-tab communication
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ source, timestamp }));
};

/**
 * Subscribe to refresh events
 * @param {Function} callback - Function to call when refresh is triggered
 * @returns {Function} Cleanup function to unsubscribe
 */
export const onRefresh = (callback) => {
    // Handle same-tab events
    const handleCustomEvent = (event) => {
        callback(event.detail);
    };
    
    // Handle cross-tab events via localStorage
    const handleStorageEvent = (event) => {
        if (event.key === STORAGE_KEY && event.newValue) {
            try {
                const data = JSON.parse(event.newValue);
                callback(data);
            } catch (e) {
                console.error('Error parsing refresh event:', e);
            }
        }
    };
    
    window.addEventListener(REFRESH_EVENT, handleCustomEvent);
    window.addEventListener('storage', handleStorageEvent);
    
    // Return cleanup function
    return () => {
        window.removeEventListener(REFRESH_EVENT, handleCustomEvent);
        window.removeEventListener('storage', handleStorageEvent);
    };
};

export default { triggerRefresh, onRefresh };
