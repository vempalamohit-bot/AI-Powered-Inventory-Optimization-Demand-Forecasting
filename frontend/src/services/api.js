import axios from 'axios';
import { cachedApiCall, cacheService } from './cacheService';

// Use injected base URL (Colab/ngrok) or default to localhost
const API_BASE_URL = window.__API_BASE__ || 'http://localhost:8000/api';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 1800000, // 30 minutes for large file uploads
});

export const productService = {
    getAll: () => api.get('/products'),
    getById: (id) => api.get(`/products/${id}`),
    // Optimized dropdown with caching - 2 minute cache
    getForDropdown: async (search = '', limit = 200) => {
        const cacheKey = cacheService.generateKey('/products/dropdown', { search, limit });
        return cachedApiCall(
            () => api.get('/products/dropdown', { params: { search, limit } }),
            cacheKey,
            { ttl: 2 * 60 * 1000 } // 2 minutes
        );
    },
    getPaginated: (page = 1, pageSize = 50, filters = {}) => 
        api.get('/products/paginated', { 
            params: { 
                page, 
                page_size: pageSize,
                category: filters.category,
                stock_filter: filters.stockFilter,
                search: filters.search
            } 
        }),
    getSummary: async () => {
        const cacheKey = 'products/summary';
        return cachedApiCall(
            () => api.get('/products/summary'),
            cacheKey,
            { ttl: 5 * 60 * 1000 } // 5 minutes
        );
    },
    getOrderingRecommendations: () => api.get('/products/ordering-recommendations'),
};

export const forecastService = {
    generate: (productId, forecastDays = 30) =>
        api.post(`/forecast/${productId}`, null, { params: { forecast_days: forecastDays } }),
    get: (productId) => api.get(`/forecast/${productId}`),
    getShadow: (productId) => api.get(`/products/${productId}/shadow-forecast`),
};

// Intelligent Forecasting Service with Multi-Model Selection
export const intelligentForecastService = {
    /**
     * Generate intelligent forecast with automatic model selection
     * Uses product segmentation to choose the best forecasting model
     * Returns: forecast, segment, model used, confidence intervals, business explanation
     */
    getIntelligentForecast: async (productId, forecastDays = 30, options = {}) => {
        const cacheKey = cacheService.generateKey(`/products/${productId}/intelligent-forecast`, { forecast_days: forecastDays });
        const ttl = options.ttl || 10 * 60 * 1000; // 10 minutes cache for forecasts
        
        return cachedApiCall(
            () => api.get(`/products/${productId}/intelligent-forecast`, { 
                params: { forecast_days: forecastDays } 
            }),
            cacheKey,
            { ttl, forceRefresh: options.forceRefresh }
        );
    },
    
    /**
     * Batch intelligent forecast for multiple products
     * Efficiently forecasts multiple products in one call
     */
    getBatchIntelligentForecast: async (productIds, forecastDays = 30) => {
        return api.post('/products/batch-intelligent-forecast', {
            product_ids: productIds,
            forecast_days: forecastDays
        });
    },
    
    /**
     * Clear forecast cache for a specific product
     */
    invalidateCache: (productId) => {
        cacheService.invalidatePattern(`/products/${productId}/intelligent-forecast`);
    },
    
    /**
     * Clear all forecast caches
     */
    clearAllCaches: () => {
        cacheService.invalidatePattern('intelligent-forecast');
    }
};

export const optimizationService = {
    optimize: (productId, serviceLevel = 0.95) =>
        api.post(`/optimize/${productId}`, null, { params: { service_level: serviceLevel } }),
    getAll: () => api.get('/optimize'),
};

export const analyticsService = {
    // Fast dashboard with caching - 3 minute cache
    getDashboard: async (period = 'daily') => {
        const cacheKey = cacheService.generateKey('/analytics/dashboard-fast', { period });
        return cachedApiCall(
            () => api.get('/analytics/dashboard-fast', { params: { period } }),
            cacheKey,
            { ttl: 3 * 60 * 1000 } // 3 minutes
        );
    },
    getDashboardFull: (period = 'daily') => api.get('/analytics/dashboard', { params: { period } }),
    getModelsInfo: () => api.get('/ai/models-info'),
    getProductSalesTrend: (productId, period = 'daily') => api.get(`/analytics/product-sales-trend/${productId}`, { params: { period } }),
    getLiveAlerts: (limit = 200) => api.get('/analytics/live-alerts', { params: { limit } }),
};

export const riskService = {
    classifySku: (productId, payload) => api.post(`/risk/profile-sku/${productId}`, payload),
    compareServiceLevels: (productId) => api.post(`/risk/compare-service-levels/${productId}`),
};

export const financialService = {
    getMonthlyReport: () => api.get('/financial/monthly-report'),
};

export const scenarioService = {
    simulatePriceChange: (productId, payload) =>
        api.post('/scenarios/price-change', null, { params: { product_id: productId, ...payload } }),
    simulateDemandShift: (productId, payload) =>
        api.post('/scenarios/demand-shift', null, { params: { product_id: productId, ...payload } }),
    simulateSupplierSwitch: (productId, payload) =>
        api.post('/scenarios/supplier-switch', null, { params: { product_id: productId, ...payload } }),
};

export const chatService = {
    ask: (message) => api.post('/chat/query', { message }),
};

export const dataService = {
    generateSampleData: (days = 90) =>
        api.post('/generate-sample-data', null, { params: { days } }),
    uploadSalesData: (file) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post('/data/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
    },
    uploadSalesFast: (file) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post('/data/upload-sales-fast', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
    },
    uploadNewProducts: (file) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post('/data/upload-new-products', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
    },
    restockInventory: (file) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post('/data/restock-inventory', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
    },
    confirmRestock: (data) => {
        return api.post('/data/restock-inventory/confirm', data);
    },
};

// AI Explainer Service - Natural Language Decision Support
export const aiExplainerService = {
    explainLoss: (productId) => api.get(`/ai/explain/loss/${productId}`),
    explainReorder: (productId) => api.get(`/ai/explain/reorder/${productId}`),
    explainForecast: (productId, forecastDays = 30) => 
        api.get(`/ai/explain/forecast/${productId}`, { params: { forecast_days: forecastDays } }),
    explainAlerts: (limit = 20) => api.get('/ai/explain/alerts', { params: { limit } }),
};

export const onboardingService = {
    smartUploadSales: (file) => {
        const formData = new FormData();
        formData.append('file', file);
        return api.post('/onboarding/smart-upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        });
    },
};

// Stock Threshold Configuration Service
export const thresholdService = {
    getThresholds: () => api.get('/settings/thresholds'),
    updateThresholds: (thresholds) => api.post('/settings/thresholds', thresholds),
    getProductsWithThresholds: (lowMax, mediumMax) => 
        api.get('/metrics/products-detail-dynamic', { 
            params: { 
                low_max: lowMax, 
                medium_max: mediumMax 
            } 
        }),
};

// JSON Ingestion Service
export const jsonIngestionService = {
    ingestData: (dataType, records, options = {}) => 
        api.post('/data/json-ingest', { data_type: dataType, records, options }),
    getModelColumns: (modelName) => api.get(`/data/model-columns/${modelName}`),
    listAllModelColumns: () => api.get('/data/model-columns'),
    prepareForModel: (modelName, includeProducts = true, includeSales = true, limit = 10000) =>
        api.post('/data/prepare-for-model', { 
            model_name: modelName, 
            include_products: includeProducts, 
            include_sales: includeSales,
            limit 
        }),
};

// Email Notification Service
export const emailService = {
    getConfig: () => api.get('/settings/email-config'),
    updateConfig: (config) => api.post('/settings/email-config', config),
    generateAlertEmail: (alertType = 'all', productIds = [], includeRecommendations = true) =>
        api.post('/alerts/generate-email', { 
            alert_type: alertType, 
            product_ids: productIds, 
            include_recommendations: includeRecommendations 
        }),
    sendEmail: (subject, emailBody, recipients = []) =>
        api.post('/alerts/send-email', { subject, email_body: emailBody, recipients }),
    getStockAlerts: () => api.get('/alerts/stock-notifications'),
    checkThresholdAlerts: () => api.get('/alerts/threshold-check'),
    sendThresholdEmail: (emailTo, alertIds = []) =>
        api.post('/alerts/send-threshold-email', null, { 
            params: { email_to: emailTo, alert_ids: alertIds.join(',') || undefined }
        }),
    getEmailPreview: () => api.get('/alerts/email-preview'),
    sendCustomEmail: (emailTo, subject, body) => {
        // Parse email addresses into array
        const recipients = emailTo.split(',').map(e => e.trim()).filter(e => e);
        // Send as JSON body, not query params
        return api.post('/alerts/send-email', {
            subject: subject,
            email_body: body,
            recipients: recipients
        });
    },
};

// External API Integration Service
export const externalApiService = {
    getTemplates: () => api.get('/data/external-api-templates'),
    importFromApi: (apiUrl, dataType = 'products') =>
        api.post('/data/import-from-api', null, {
            params: { api_url: apiUrl, data_type: dataType }
        }),
};

// Settings Service
export const settingsService = {
    getEmailConfig: () => api.get('/settings/email-config'),
    updateEmailConfig: (config) => api.post('/settings/email-config', config),
};

export default api;
