import React, { useState, useEffect } from 'react';
import { optimizationService, analyticsService } from '../services/api';
import { onRefresh } from '../services/refreshService';
import { frontendCache } from '../services/cache';

const Optimization = () => {
    const [recommendations, setRecommendations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModelsModal, setShowModelsModal] = useState(false);
    const [modelsInfo, setModelsInfo] = useState(null);

    useEffect(() => {
        loadRecommendations();
    }, []);

    // Listen for data refresh events from Products page (upload/restock)
    useEffect(() => {
        const cleanup = onRefresh((data) => {
            console.log('Optimization refreshing due to:', data.source);
            loadRecommendations();
        });
        return cleanup;
    }, []);

    const loadRecommendations = async () => {
        try {
            // Check cache (60 second TTL for recommendations)
            const cacheKey = 'recommendations';
            const cached = frontendCache.get(cacheKey, 60);
            if (cached) {
                setRecommendations(cached);
                setLoading(false);
                return;
            }
            
            const response = await optimizationService.getAll();
            setRecommendations(response.data);
            
            // Cache the result
            frontendCache.set(cacheKey, response.data);
        } catch (error) {
            console.error('Error loading recommendations:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadModelsInfo = async () => {
        try {
            const response = await analyticsService.getModelsInfo();
            setModelsInfo(response.data);
            setShowModelsModal(true);
        } catch (error) {
            console.error('Error loading models info:', error);
            alert('Failed to load models information');
        }
    };

    const totalSavings = recommendations.reduce((sum, rec) => sum + (rec.estimated_savings || 0), 0);
    const needsReorder = recommendations.filter(rec => rec.needs_reorder).length;

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
                <div className="spinner"></div>
            </div>
        );
    }

    return (
        <div className="container" style={{ padding: 'var(--spacing-lg) var(--spacing-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-4)' }}>
                <h1>Inventory Optimization</h1>
                <button className="btn btn-secondary" onClick={loadModelsInfo} style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-2)' }}>
                    <span>⚙️</span> Models Info
                </button>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-3 mb-3">
                <div className="metric-card">
                    <div className="metric-icon" style={{ background: 'var(--gradient-primary)' }}>
                        📦
                    </div>
                    <div className="metric-content">
                        <div className="metric-label">Products Analyzed</div>
                        <div className="metric-value">{recommendations.length}</div>
                    </div>
                </div>

                <div className="metric-card">
                    <div className="metric-icon" style={{ background: 'var(--gradient-danger)' }}>
                        🔔
                    </div>
                    <div className="metric-content">
                        <div className="metric-label">Needs Reorder</div>
                        <div className="metric-value">{needsReorder}</div>
                    </div>
                </div>

                <div className="metric-card">
                    <div className="metric-icon" style={{ background: 'var(--gradient-success)' }}>
                        💰
                    </div>
                    <div className="metric-content">
                        <div className="metric-label">Total Savings</div>
                        <div className="metric-value">${totalSavings.toLocaleString()}</div>
                    </div>
                </div>
            </div>

            {/* Recommendations Table */}
            {recommendations.length === 0 ? (
                <div className="card text-center" style={{ padding: 'var(--spacing-xl)' }}>
                    <h3>No Recommendations Available</h3>
                    <p style={{ color: 'var(--text-secondary)', marginTop: 'var(--spacing-sm)' }}>
                        Generate optimization recommendations for your products first
                    </p>
                </div>
            ) : (
                <div className="card">
                    <h3 className="mb-2">Optimization Recommendations</h3>
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Product</th>
                                    <th title="How many units are currently in stock">Current Stock</th>
                                    <th title="Order more when stock reaches this level">When to Reorder</th>
                                    <th title="Buffer units to prevent stockouts">Safety Buffer</th>
                                    <th title="The optimal quantity to order each time">Order Quantity</th>
                                    <th title="The ideal stock level to maintain">Target Level</th>
                                    <th title="Estimated annual cost savings from following these recommendations">Est. Savings</th>
                                    <th>Action</th>
                                </tr>
                            </thead>
                            <tbody>
                                {recommendations.map((rec) => (
                                    <tr key={rec.product_id} style={{ background: rec.needs_reorder ? 'rgba(255, 107, 107, 0.05)' : 'transparent' }}>
                                        <td>
                                            <div style={{ fontWeight: 600 }}>{rec.product_name}</div>
                                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                                                {rec.sku}
                                            </div>
                                        </td>
                                        <td>
                                            <span style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                                                {rec.current_stock}
                                            </span>
                                        </td>
                                        <td>
                                            <span style={{ color: 'var(--accent-warning)' }}>
                                                {rec.reorder_point.toFixed(0)}
                                            </span>
                                        </td>
                                        <td>{rec.safety_stock.toFixed(0)}</td>
                                        <td>
                                            <span style={{ color: 'var(--accent-primary)' }}>
                                                {rec.economic_order_quantity.toFixed(0)}
                                            </span>
                                        </td>
                                        <td>
                                            <span style={{ color: 'var(--accent-success)' }}>
                                                {rec.optimal_stock_level.toFixed(0)}
                                            </span>
                                        </td>
                                        <td>
                                            <span style={{ color: 'var(--accent-success)', fontWeight: 600 }}>
                                                ${rec.estimated_savings.toLocaleString()}
                                            </span>
                                        </td>
                                        <td>
                                            {rec.needs_reorder ? (
                                                <span className="badge badge-danger">
                                                    ⚠️ Reorder Now
                                                </span>
                                            ) : (
                                                <span className="badge badge-success">
                                                    ✓ Adequate
                                                </span>
                                            )}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Info Section */}
            {/* AI-Powered What This Means Section */}
            <div style={{ 
                background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
                borderRadius: '12px',
                padding: '1.25rem 1.5rem',
                marginTop: 'var(--spacing-3)',
                marginBottom: 'var(--spacing-3)',
                borderLeft: '4px solid #4a6fa5'
            }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
                    <span style={{ fontSize: '1.5rem' }}>💡</span>
                    <div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.5rem', fontWeight: '600', letterSpacing: '0.5px' }}>
                            SMART INVENTORY ASSISTANT
                        </div>
                        <div style={{ fontSize: '0.9rem', color: '#334155', lineHeight: '1.7' }}>
                            <strong>What this table shows:</strong> We've analyzed your sales patterns and calculated the optimal inventory levels for each product. 
                            Products marked <span style={{ color: '#b84444' }}>"Reorder Now"</span> need attention — their stock is below the safe level. 
                            The <strong>"Est. Savings"</strong> column shows how much money you could save annually by following these recommendations instead of manual ordering.
                        </div>
                    </div>
                </div>
            </div>

            <div className="grid grid-2 mt-3">
                <div className="card">
                    <h3 className="mb-2">What These Numbers Mean</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
                        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                            <span style={{ fontSize: '1.25rem' }}>📋</span>
                            <div>
                                <h4 style={{ fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                                    When to Reorder (Reorder Point)
                                </h4>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: '1.5' }}>
                                    When your stock drops to this number, it's time to place an order. We calculate this based on how fast items sell and how long your supplier takes to deliver.
                                </p>
                            </div>
                        </div>
                        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                            <span style={{ fontSize: '1.25rem' }}>🛡️</span>
                            <div>
                                <h4 style={{ fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                                    Safety Buffer
                                </h4>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: '1.5' }}>
                                    Extra units to cover unexpected spikes in demand or delivery delays. Think of it as insurance against running out.
                                </p>
                            </div>
                        </div>
                        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                            <span style={{ fontSize: '1.25rem' }}>📦</span>
                            <div>
                                <h4 style={{ fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                                    Order Quantity
                                </h4>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: '1.5' }}>
                                    The smartest number of units to order at once. This balances the cost of ordering frequently vs. the cost of storing too much inventory.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="card">
                    <h3 className="mb-2">How You Save Money</h3>
                    <div style={{ 
                        background: 'linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)',
                        borderRadius: '8px',
                        padding: '1rem',
                        marginBottom: '1rem',
                        borderLeft: '3px solid #3d6b47'
                    }}>
                        <div style={{ fontSize: '0.85rem', color: '#064e3b', lineHeight: '1.6' }}>
                            <strong>The "Est. Savings" in the table above</strong> shows yearly savings from following these recommendations vs. manual inventory management. 
                            Companies typically overspend on excess stock or lose sales from running out. This system helps you find the right balance.
                        </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
                        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                            <span style={{ fontSize: '1.25rem' }}>📉</span>
                            <div>
                                <strong style={{ color: 'var(--text-primary)', fontSize: '0.9rem' }}>Less money tied up in excess stock</strong>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: '0.25rem 0 0 0' }}>
                                    Every item sitting on a shelf costs ~25% of its value per year in storage and capital costs
                                </p>
                            </div>
                        </div>
                        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                            <span style={{ fontSize: '1.25rem' }}>🚫</span>
                            <div>
                                <strong style={{ color: 'var(--text-primary)', fontSize: '0.9rem' }}>Fewer stockouts and lost sales</strong>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: '0.25rem 0 0 0' }}>
                                    When you run out of stock, customers buy elsewhere — smart forecasting prevents this
                                </p>
                            </div>
                        </div>
                        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                            <span style={{ fontSize: '1.25rem' }}>📦</span>
                            <div>
                                <strong style={{ color: 'var(--text-primary)', fontSize: '0.9rem' }}>Smarter ordering</strong>
                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: '0.25rem 0 0 0' }}>
                                    Order the right amount at the right time to minimize both ordering and storage costs
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Models Info Modal */}}
            {showModelsModal && modelsInfo && (
                <div className="modal-overlay" onClick={() => setShowModelsModal(false)}>
                    <div className="modal-content" style={{ maxWidth: '900px', maxHeight: '80vh', overflow: 'auto' }} onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>⚙️ Forecasting Models & Algorithms</h2>
                            <button className="modal-close" onClick={() => setShowModelsModal(false)}>×</button>
                        </div>
                        <div className="modal-body">
                            {/* Forecasting Models */}
                            <h3 style={{ marginTop: 'var(--spacing-4)', color: 'var(--accent-primary)' }}>📈 Forecasting Models</h3>
                            <div style={{ background: 'var(--color-gray-50)', padding: 'var(--spacing-4)', borderRadius: '8px', marginBottom: 'var(--spacing-4)' }}>
                                <h4>{modelsInfo.forecasting_models.primary.name}</h4>
                                <p><strong>Library:</strong> {modelsInfo.forecasting_models.primary.library}</p>
                                <p>{modelsInfo.forecasting_models.primary.description}</p>
                                <p><strong>Parameters:</strong> Seasonal periods: {modelsInfo.forecasting_models.primary.parameters.seasonal_periods}, Trend: {modelsInfo.forecasting_models.primary.parameters.trend}</p>
                                
                                <h4 style={{ marginTop: 'var(--spacing-3)' }}>{modelsInfo.forecasting_models.secondary.name}</h4>
                                <p><strong>Library:</strong> {modelsInfo.forecasting_models.secondary.library}</p>
                                <p>{modelsInfo.forecasting_models.secondary.description}</p>
                                <p><strong>Features:</strong> {modelsInfo.forecasting_models.secondary.features.join(', ')}</p>
                                
                                <div style={{ background: '#E0F2FE', padding: 'var(--spacing-3)', borderRadius: '6px', marginTop: 'var(--spacing-3)' }}>
                                    <h4>🎯 {modelsInfo.forecasting_models.ensemble.name}</h4>
                                    <p>{modelsInfo.forecasting_models.ensemble.description}</p>
                                    <p><strong>Weights:</strong> Exponential Smoothing: {modelsInfo.forecasting_models.ensemble.weights.exponential_smoothing * 100}%, Linear Regression: {modelsInfo.forecasting_models.ensemble.weights.linear_regression * 100}%</p>
                                </div>
                            </div>

                            {/* Optimization Algorithms */}
                            <h3 style={{ marginTop: 'var(--spacing-4)', color: 'var(--accent-primary)' }}>⚙️ Optimization Algorithms</h3>
                            <div style={{ background: 'var(--color-gray-50)', padding: 'var(--spacing-4)', borderRadius: '8px', marginBottom: 'var(--spacing-4)' }}>
                                {Object.entries(modelsInfo.optimization_algorithms).map(([key, algo]) => (
                                    <div key={key} style={{ marginBottom: 'var(--spacing-3)', paddingBottom: 'var(--spacing-3)', borderBottom: key === 'safety_stock' ? 'none' : '1px solid var(--border-color)' }}>
                                        <h4>{algo.name}</h4>
                                        <p><strong>Type:</strong> {algo.type}</p>
                                        <p><strong>Formula:</strong> <code style={{ background: '#FEF3C7', padding: '2px 8px', borderRadius: '4px' }}>{algo.formula}</code></p>
                                        <p>{algo.description}</p>
                                    </div>
                                ))}
                            </div>

                            {/* Pricing Algorithms */}
                            <h3 style={{ marginTop: 'var(--spacing-4)', color: 'var(--accent-primary)' }}>💰 Pricing Algorithms</h3>
                            <div style={{ background: 'var(--color-gray-50)', padding: 'var(--spacing-4)', borderRadius: '8px', marginBottom: 'var(--spacing-4)' }}>
                                <h4>{modelsInfo.pricing_algorithms.markdown.name}</h4>
                                <p>{modelsInfo.pricing_algorithms.markdown.description}</p>
                                <p><strong>Trigger:</strong> {modelsInfo.pricing_algorithms.markdown.trigger}</p>
                                <p><strong>Discount Rate:</strong> {modelsInfo.pricing_algorithms.markdown.discount_rate}</p>
                            </div>

                            {/* Cost Parameters */}
                            <h3 style={{ marginTop: 'var(--spacing-4)', color: 'var(--accent-primary)' }}>📊 Cost Parameters</h3>
                            <div style={{ background: 'var(--color-gray-50)', padding: 'var(--spacing-4)', borderRadius: '8px', marginBottom: 'var(--spacing-4)' }}>
                                {Object.entries(modelsInfo.cost_parameters).map(([key, param]) => (
                                    <div key={key} style={{ marginBottom: 'var(--spacing-2)' }}>
                                        <strong>{key.replace(/_/g, ' ').toUpperCase()}:</strong>
                                        <p>{typeof param.value === 'number' ? `${param.value * (key.includes('rate') ? 100 : 1)}${param.currency ? ' ' + param.currency : key.includes('rate') ? '%' : ''}` : param.value}</p>
                                        <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{param.description}</p>
                                    </div>
                                ))}
                            </div>

                            {/* Accuracy Metrics */}
                            <h3 style={{ marginTop: 'var(--spacing-4)', color: 'var(--accent-primary)' }}>🎯 Accuracy Metrics</h3>
                            <div style={{ background: 'var(--color-gray-50)', padding: 'var(--spacing-4)', borderRadius: '8px' }}>
                                {Object.entries(modelsInfo.accuracy_metrics).map(([key, description]) => (
                                    <div key={key} style={{ marginBottom: 'var(--spacing-2)' }}>
                                        <strong>{key.toUpperCase()}:</strong> {description}
                                    </div>
                                ))}
                            </div>
                        </div>
                        <div className="modal-footer">
                            <button className="btn btn-secondary" onClick={() => setShowModelsModal(false)}>Close</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Optimization;
