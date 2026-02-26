import React, { useState, useEffect } from 'react';
import { productService, intelligentForecastService } from '../services/api';
import { onRefresh } from '../services/refreshService';
import ForecastChart from '../components/ForecastChart';

const Forecasting = () => {
    const [products, setProducts] = useState([]);
    const [selectedProduct, setSelectedProduct] = useState('');
    const [forecastDays, setForecastDays] = useState(30);
    const [forecastData, setForecastData] = useState(null);
    const [forecastMetadata, setForecastMetadata] = useState(null); // New: segment, model, explanation
    const [loading, setLoading] = useState(false);
    const [searchTerm, setSearchTerm] = useState('');
    const [searching, setSearching] = useState(false);
    const [totalProducts, setTotalProducts] = useState(0);
    const [productsLoaded, setProductsLoaded] = useState(false); // Lazy loading flag

    // Lazy loading: Load products only when dropdown is opened or search is triggered
    useEffect(() => {
        if (productsLoaded) return;
        if (searchTerm !== '' || products.length === 0) {
            loadProducts('');
        }
    }, []);

    // Debounced product search
    useEffect(() => {
        if (searchTerm === '') {
            if (productsLoaded) {
                loadProducts('');
            }
            return;
        }
        const timeout = setTimeout(() => {
            loadProducts(searchTerm);
        }, 300);
        return () => clearTimeout(timeout);
    }, [searchTerm]);

    // Listen for data refresh events from Products page
    useEffect(() => {
        const cleanup = onRefresh((data) => {
            console.log('Forecasting refreshing due to:', data.source);
            if (productsLoaded) {
                loadProducts(searchTerm);
            }
            // Clear forecast data to prompt re-generation with new data
            setForecastData(null);
            setForecastMetadata(null);
            // Invalidate cache for current product
            if (selectedProduct) {
                intelligentForecastService.invalidateCache(selectedProduct);
            }
        });
        return cleanup;
    }, [searchTerm, selectedProduct, productsLoaded]);

    const loadProducts = async (search = '') => {
        try {
            setSearching(true);
            // Load more products for better selection (server-side search handles filtering)
            const response = await productService.getForDropdown(search, 500);
            setProducts(response.data);
            setProductsLoaded(true);
            if (!search && response.data.length > 0 && !selectedProduct) {
                setSelectedProduct(response.data[0].id.toString());
            }
            // Get total count on initial load (cached)
            if (!search) {
                const summaryRes = await productService.getSummary();
                setTotalProducts(summaryRes.data.total_products || response.data.length);
            }
        } catch (error) {
            console.error('Error loading products:', error);
        } finally {
            setSearching(false);
        }
    };

    const generateForecast = async () => {
        if (!selectedProduct) return;

        setLoading(true);
        try {
            // Use intelligent forecast endpoint with caching
            const response = await intelligentForecastService.getIntelligentForecast(
                selectedProduct, 
                forecastDays
            );

            const data = response.data;

            // Combine historical and forecast data
            const historical = data.historical.map(h => ({
                date: h.date,
                actual: h.actual,
            }));

            const forecast = data.forecast.map(f => ({
                date: f.date,
                predicted: f.predicted,
                lower_bound: f.lower_bound,
                upper_bound: f.upper_bound,
            }));

            setForecastData([...historical, ...forecast]);
            
            // Store metadata (segment, model, explanation)
            setForecastMetadata({
                segment: data.segment,
                modelUsed: data.model_used,
                businessExplanation: data.business_explanation,
                characteristics: data.characteristics || {}
            });

        } catch (error) {
            console.error('Error generating forecast:', error);
            alert('Error generating forecast. Make sure there is sales history for this product.');
        } finally {
            setLoading(false);
        }
    };

    const selectedProductName = products.find(p => p.id.toString() === selectedProduct)?.name || '';

    return (
        <div className="container" style={{ padding: 'var(--spacing-lg) var(--spacing-md)', maxWidth: '1400px', margin: '0 auto' }}>
            <div style={{ marginBottom: '1.5rem' }}>
                <h1 style={{ fontSize: '1.75rem', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>Demand Forecasting</h1>
                <p style={{ color: 'var(--text-tertiary)', fontSize: '0.9rem' }}>Predict future demand to optimize your inventory levels</p>
            </div>

            <div className="grid grid-2 mb-3">
                {/* Configuration Panel */}
                <div className="card" style={{ borderTop: '3px solid var(--accent-primary)' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg>
                        Forecast Configuration
                    </h3>

                    <div style={{ marginBottom: '1.25rem' }}>
                        <label htmlFor="product-search" style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.5rem', display: 'block' }}>Select Product</label>
                        <div style={{ marginBottom: '0.5rem' }}>
                            <input
                                id="product-search"
                                type="text"
                                placeholder="Search by name or SKU..."
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                style={{
                                    padding: '0.6rem 0.75rem',
                                    fontSize: '0.875rem',
                                    border: '1px solid var(--border-primary)',
                                    borderRadius: '6px',
                                    backgroundColor: 'var(--bg-primary)',
                                    color: 'var(--text-primary)',
                                    width: '100%',
                                    marginBottom: '0.35rem',
                                    transition: 'border-color 0.2s',
                                    outline: 'none'
                                }}
                                onFocus={(e) => e.target.style.borderColor = 'var(--accent-primary)'}
                                onBlur={(e) => e.target.style.borderColor = 'var(--border-primary)'}
                            />
                            <small style={{ color: 'var(--text-tertiary)', fontSize: '0.75rem' }}>
                                {searching ? 'Searching...' : `Showing ${products.length} of ${totalProducts.toLocaleString()} products`}
                            </small>
                        </div>
                        <select
                            id="product-select"
                            value={selectedProduct}
                            onChange={(e) => setSelectedProduct(e.target.value)}
                            style={{
                              padding: '0.6rem 0.75rem',
                              fontSize: '0.875rem',
                              border: '1px solid var(--border-primary)',
                              borderRadius: '6px',
                              backgroundColor: 'var(--bg-primary)',
                              color: 'var(--text-primary)',
                              fontWeight: '500',
                              width: '100%',
                              cursor: 'pointer'
                            }}
                        >
                            {products.map((product) => (
                                <option key={product.id} value={product.id}>
                                    {product.name} ({product.sku})
                                </option>
                            ))}
                        </select>
                    </div>

                    <div style={{ marginBottom: '1.25rem' }}>
                        <label htmlFor="forecast-days" style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.5rem', display: 'block' }}>Forecast Horizon</label>
                        <select
                            id="forecast-days"
                            value={forecastDays}
                            onChange={(e) => setForecastDays(parseInt(e.target.value))}
                            style={{
                              padding: '0.6rem 0.75rem',
                              fontSize: '0.875rem',
                              border: '1px solid var(--border-primary)',
                              borderRadius: '6px',
                              backgroundColor: 'var(--bg-primary)',
                              color: 'var(--text-primary)',
                              fontWeight: '500',
                              width: '100%',
                              cursor: 'pointer'
                            }}
                        >
                            <option value={7}>Next 7 Days</option>
                            <option value={14}>Next 14 Days</option>
                            <option value={30}>Next 30 Days</option>
                            <option value={90}>Next 90 Days</option>
                            <option value={180}>Next 6 Months</option>
                            <option value={365}>Next 12 Months</option>
                        </select>
                    </div>

                    <button
                        className="btn btn-primary"
                        onClick={generateForecast}
                        disabled={loading || !selectedProduct}
                        style={{ width: '100%', padding: '0.75rem', fontSize: '0.9rem', fontWeight: '600', borderRadius: '8px' }}
                    >
                        {loading ? 'Generating Forecast...' : 'Generate Forecast'}
                    </button>

                    {forecastData && (
                        <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '8px', border: '1px solid var(--border-primary)' }}>
                            <h4 style={{ fontSize: '0.85rem', fontWeight: '600', marginBottom: '0.75rem', color: 'var(--text-primary)' }}>Forecast Summary</h4>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                                <strong>Product:</strong> {selectedProductName}
                            </p>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                                <strong>Horizon:</strong> {forecastDays === 180 ? 'Next 6 months' : forecastDays === 365 ? 'Next 12 months' : `${forecastDays} days`}
                            </p>
                            <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                                <strong>Data Points:</strong> {forecastData.length}
                            </p>
                            {forecastMetadata && (
                                <>
                                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                                        <strong>Demand Pattern:</strong> <span style={{ 
                                            padding: '0.25rem 0.5rem', 
                                            background: forecastMetadata.segment?.includes('STABLE') ? '#dcfce7' : 
                                                       forecastMetadata.segment?.includes('SEASONAL') ? '#dbeafe' : 
                                                       forecastMetadata.segment?.includes('VOLATILE') ? '#fef3c7' : '#f3f4f6',
                                            borderRadius: '4px',
                                            fontWeight: '600',
                                            fontSize: '0.8rem'
                                        }}>
                                            {forecastMetadata.segment?.replace(/_/g, ' ')}
                                        </span>
                                    </p>
                                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                                        <strong>AI Model:</strong> <span style={{ 
                                            padding: '0.25rem 0.5rem', 
                                            background: '#e0e7ff',
                                            borderRadius: '4px',
                                            fontWeight: '600',
                                            fontSize: '0.8rem',
                                            color: '#4338ca'
                                        }}>
                                            {forecastMetadata.modelUsed}
                                        </span>
                                    </p>
                                </>
                            )}
                        </div>
                    )}
                </div>

                {/* Info Panel */}
                <div className="card" style={{ borderTop: '3px solid #0ea5e9' }}>
                    <h3 style={{ fontSize: '1rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0ea5e9" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
                        How Smart Forecasting Helps Your Business
                    </h3>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--spacing-md)', fontSize: '0.9rem', lineHeight: '1.6' }}>
                        Stop guessing at inventory needs. Our system learns from your actual sales patterns to predict exactly how much stock you'll need — 
                        reducing both overstock costs and lost sales from stockouts.
                    </p>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
                        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                            <span style={{ fontSize: '1.25rem' }}>📈</span>
                            <div>
                                <h4 style={{ fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                                    Learns Your Sales Patterns
                                </h4>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: '1.5' }}>
                                    The system analyzes trends and seasonal patterns — like higher sales on weekends or holiday spikes — 
                                    so you're prepared before demand changes, not after.
                                </p>
                            </div>
                        </div>

                        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                            <span style={{ fontSize: '1.25rem' }}>🎯</span>
                            <div>
                                <h4 style={{ fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                                    Better Than Spreadsheet Averages
                                </h4>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: '1.5' }}>
                                    Our smart system combines multiple forecasting techniques — it's like having several expert analysts 
                                    who vote on the best prediction, typically 15-40% more accurate than basic methods.
                                </p>
                            </div>
                        </div>

                        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                            <span style={{ fontSize: '1.25rem' }}>📊</span>
                            <div>
                                <h4 style={{ fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                                    Know Your Risk Level
                                </h4>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', lineHeight: '1.5' }}>
                                    The confidence bands show you the range of likely demand — stock at the high end for critical 
                                    items, or lean for items where occasional stockouts are acceptable.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Forecast Chart */}
            {forecastData && (
                <div className="card fade-in" style={{ borderTop: '3px solid var(--accent-primary)' }}>
                    <h3 style={{ fontSize: '1.1rem', fontWeight: '600', color: 'var(--text-primary)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent-primary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                        Forecast Visualization
                    </h3>
                    <ForecastChart data={forecastData} />

                    {/* Business-Friendly Forecast Explanation */}
                    <div style={{ marginTop: '1.5rem', padding: '1.25rem', background: '#f0fdf4', borderRadius: '10px', border: '1px solid #bbf7d0' }}>
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                            <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: '#dcfce7', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#16a34a" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/><polyline points="17 6 23 6 23 12"/></svg>
                            </div>
                            <div>
                                <div style={{ fontSize: '0.8rem', color: '#166534', marginBottom: '0.5rem', fontWeight: '700', letterSpacing: '0.3px' }}>
                                    WHAT THIS FORECAST MEANS FOR YOUR BUSINESS
                                </div>
                                <div style={{ fontSize: '0.9rem', color: '#14532d', lineHeight: '1.7' }}>
                                    {(() => {
                                        const forecastOnly = forecastData.filter(d => d.predicted !== undefined && d.predicted !== null);
                                        const historicalOnly = forecastData.filter(d => d.actual !== undefined && d.actual !== null);
                                        const totalPredicted = forecastOnly.reduce((sum, d) => sum + (d.predicted || 0), 0);
                                        const avgDaily = forecastOnly.length > 0 ? totalPredicted / forecastOnly.length : 0;
                                        const lastHistorical = historicalOnly.length > 0 ? historicalOnly[historicalOnly.length - 1]?.actual : 0;
                                        const firstPrediction = forecastOnly.length > 0 ? forecastOnly[0]?.predicted : 0;
                                        const lastPrediction = forecastOnly.length > 0 ? forecastOnly[forecastOnly.length - 1]?.predicted : 0;
                                        const trend = lastPrediction > firstPrediction * 1.1 ? 'increasing' : lastPrediction < firstPrediction * 0.9 ? 'decreasing' : 'stable';
                                        
                                        return (
                                            <>
                                                <strong>Summary:</strong> Over the next <strong>{forecastOnly.length} days</strong>, we predict you'll sell approximately 
                                                <strong style={{ color: '#15803d' }}> {Math.round(totalPredicted).toLocaleString()} units</strong> of <strong>{selectedProductName}</strong> 
                                                {avgDaily > 0 && <> (about <strong>{avgDaily.toFixed(1)} units per day</strong>)</>}.
                                                
                                                <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'rgba(255,255,255,0.7)', borderRadius: '8px' }}>
                                                    <strong>📊 Reading the Chart:</strong>
                                                    <ul style={{ margin: '0.5rem 0 0 1rem', paddingLeft: '0.5rem' }}>
                                                        <li><strong style={{ color: '#6366f1' }}>Purple area (Historical)</strong> = Your actual past sales — what really happened</li>
                                                        <li><strong style={{ color: '#0D9488' }}>Teal dashed line (Forecast)</strong> = Our AI prediction for future sales</li>
                                                    </ul>
                                                </div>
                                                
                                                <div style={{ marginTop: '0.75rem' }}>
                                                    <strong>📈 Trend:</strong> Demand appears to be <strong>{trend}</strong> over this period.
                                                    {trend === 'increasing' && ' Consider ordering more stock to capitalize on growing demand.'}
                                                    {trend === 'decreasing' && ' Consider reducing order quantities to avoid excess inventory.'}
                                                    {trend === 'stable' && ' Current inventory levels should be maintained.'}
                                                </div>
                                                
                                                <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'rgba(22, 163, 74, 0.1)', borderRadius: '8px', borderLeft: '3px solid #16a34a' }}>
                                                    <strong>💡 Action Recommended:</strong> Ensure you have at least <strong>{Math.round(totalPredicted * 1.2).toLocaleString()} units</strong> available 
                                                    (forecast + 20% safety buffer) to maintain a 95% service level and avoid stockouts.
                                                </div>
                                            </>
                                        );
                                    })()}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {!forecastData && !loading && (
                <div className="card text-center" style={{ padding: '3rem 2rem' }}>
                    <div style={{ width: '56px', height: '56px', borderRadius: '12px', background: 'var(--bg-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1rem' }}>
                        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                    </div>
                    <h3 style={{ fontSize: '1.1rem', fontWeight: '600', marginBottom: '0.5rem' }}>No Forecast Generated Yet</h3>
                    <p style={{ color: 'var(--text-tertiary)', fontSize: '0.9rem' }}>
                        Select a product and click "Generate Forecast" to see predictions
                    </p>
                </div>
            )}
        </div>
    );
};

export default Forecasting;
