import React, { useState, useEffect, useMemo } from 'react';
import { optimizationService, analyticsService } from '../services/api';
import { onRefresh } from '../services/refreshService';
import { frontendCache } from '../services/cache';

const Optimization = () => {
    const [recommendations, setRecommendations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showModelsModal, setShowModelsModal] = useState(false);
    const [modelsInfo, setModelsInfo] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [sortBy, setSortBy] = useState('savings');
    const [filterStatus, setFilterStatus] = useState('all');
    const [expandedCards, setExpandedCards] = useState(new Set());
    const [viewMode, setViewMode] = useState('cards');

    useEffect(() => {
        loadRecommendations();
    }, []);

    useEffect(() => {
        const cleanup = onRefresh((data) => {
            console.log('Optimization refreshing due to:', data.source);
            loadRecommendations();
        });
        return cleanup;
    }, []);

    const loadRecommendations = async () => {
        try {
            const cacheKey = 'recommendations';
            const cached = frontendCache.get(cacheKey, 60);
            if (cached) {
                setRecommendations(cached);
                setLoading(false);
                return;
            }
            const response = await optimizationService.getAll();
            setRecommendations(response.data);
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

    const filteredAndSorted = useMemo(() => {
        let items = [...recommendations];
        if (searchTerm) {
            const q = searchTerm.toLowerCase();
            items = items.filter(rec =>
                rec.product_name?.toLowerCase().includes(q) ||
                rec.sku?.toLowerCase().includes(q) ||
                rec.category?.toLowerCase().includes(q)
            );
        }
        if (filterStatus === 'reorder') items = items.filter(rec => rec.needs_reorder);
        else if (filterStatus === 'adequate') items = items.filter(rec => !rec.needs_reorder);

        items.sort((a, b) => {
            switch (sortBy) {
                case 'savings': return (b.estimated_savings || 0) - (a.estimated_savings || 0);
                case 'urgency': return (b.needs_reorder ? 1 : 0) - (a.needs_reorder ? 1 : 0) || (a.current_stock - a.reorder_point) - (b.current_stock - b.reorder_point);
                case 'name': return (a.product_name || '').localeCompare(b.product_name || '');
                case 'stock': return a.current_stock - b.current_stock;
                default: return 0;
            }
        });
        return items;
    }, [recommendations, searchTerm, sortBy, filterStatus]);

    const toggleExpand = (id) => {
        setExpandedCards(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id); else next.add(id);
            return next;
        });
    };

    const getStockHealth = (rec) => {
        if (rec.current_stock <= 0) return { label: 'Out of Stock', color: '#dc2626', bg: '#fef2f2', pct: 0 };
        const ratio = rec.current_stock / (rec.optimal_stock_level || 1);
        if (rec.needs_reorder) return { label: 'Reorder Now', color: '#dc2626', bg: '#fef2f2', pct: Math.min(ratio * 100, 100) };
        if (ratio < 0.5) return { label: 'Low Stock', color: '#ea580c', bg: '#fff7ed', pct: ratio * 100 };
        if (ratio > 1.5) return { label: 'Overstocked', color: '#2563eb', bg: '#eff6ff', pct: 100 };
        return { label: 'Healthy', color: '#16a34a', bg: '#f0fdf4', pct: ratio * 100 };
    };

    if (loading) {
        return (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '400px' }}>
                <div className="spinner"></div>
            </div>
        );
    }

    return (
        <div className="container" style={{ padding: 'var(--spacing-lg) var(--spacing-md)', maxWidth: '1400px', margin: '0 auto' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <div>
                    <h1 style={{ fontSize: '1.75rem', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>Inventory Optimization</h1>
                    <p style={{ color: 'var(--text-tertiary)', fontSize: '0.9rem' }}>AI-driven recommendations to minimize costs and prevent stockouts</p>
                </div>
                <button className="btn btn-secondary" onClick={loadModelsInfo} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span>⚙️</span> Models Info
                </button>
            </div>

            {/* Summary Cards - clickable filters */}
            <div className="grid grid-3 mb-3">
                <div className="metric-card" style={{ cursor: 'pointer', border: filterStatus === 'all' ? '2px solid var(--accent-primary)' : undefined }} onClick={() => setFilterStatus('all')}>
                    <div className="metric-icon" style={{ background: 'var(--gradient-primary)' }}>📦</div>
                    <div className="metric-content">
                        <div className="metric-label">Products Analyzed</div>
                        <div className="metric-value">{recommendations.length}</div>
                    </div>
                </div>
                <div className="metric-card" style={{ cursor: 'pointer', border: filterStatus === 'reorder' ? '2px solid #dc2626' : undefined }} onClick={() => setFilterStatus(f => f === 'reorder' ? 'all' : 'reorder')}>
                    <div className="metric-icon" style={{ background: 'var(--gradient-danger)' }}>🔔</div>
                    <div className="metric-content">
                        <div className="metric-label">Needs Reorder</div>
                        <div className="metric-value" style={{ color: '#dc2626' }}>{needsReorder}</div>
                    </div>
                </div>
                <div className="metric-card" style={{ cursor: 'pointer', border: filterStatus === 'adequate' ? '2px solid #16a34a' : undefined }} onClick={() => setFilterStatus(f => f === 'adequate' ? 'all' : 'adequate')}>
                    <div className="metric-icon" style={{ background: 'var(--gradient-success)' }}>💰</div>
                    <div className="metric-content">
                        <div className="metric-label">Est. Annual Savings</div>
                        <div className="metric-value" style={{ color: '#16a34a' }}>${totalSavings.toLocaleString()}</div>
                    </div>
                </div>
            </div>

            {/* Search, Sort & View Controls */}
            <div className="card" style={{ padding: '1rem 1.25rem', marginBottom: '1rem' }}>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
                    <div style={{ flex: '1 1 280px', position: 'relative' }}>
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)' }}>
                            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                        </svg>
                        <input type="text" placeholder="Search by name, SKU, or category..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
                            style={{ width: '100%', padding: '0.6rem 0.75rem 0.6rem 2.25rem', fontSize: '0.875rem', border: '1px solid var(--border-primary)', borderRadius: '8px', backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)', outline: 'none' }}
                        />
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)', fontWeight: 600, whiteSpace: 'nowrap' }}>Sort:</span>
                        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} style={{ padding: '0.5rem 0.75rem', fontSize: '0.85rem', border: '1px solid var(--border-primary)', borderRadius: '6px', backgroundColor: 'var(--bg-primary)', color: 'var(--text-primary)', cursor: 'pointer' }}>
                            <option value="savings">Highest Savings</option>
                            <option value="urgency">Most Urgent</option>
                            <option value="stock">Lowest Stock</option>
                            <option value="name">Name A-Z</option>
                        </select>
                    </div>
                    <div style={{ display: 'flex', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border-primary)' }}>
                        <button onClick={() => setViewMode('cards')} style={{ padding: '0.45rem 0.85rem', fontSize: '0.8rem', border: 'none', cursor: 'pointer', backgroundColor: viewMode === 'cards' ? 'var(--accent-primary)' : 'var(--bg-primary)', color: viewMode === 'cards' ? '#fff' : 'var(--text-secondary)', transition: 'all 0.2s' }}>Cards</button>
                        <button onClick={() => setViewMode('table')} style={{ padding: '0.45rem 0.85rem', fontSize: '0.8rem', border: 'none', cursor: 'pointer', borderLeft: '1px solid var(--border-primary)', backgroundColor: viewMode === 'table' ? 'var(--accent-primary)' : 'var(--bg-primary)', color: viewMode === 'table' ? '#fff' : 'var(--text-secondary)', transition: 'all 0.2s' }}>Table</button>
                    </div>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)', marginTop: '0.5rem' }}>
                    Showing {filteredAndSorted.length} of {recommendations.length} products
                    {filterStatus !== 'all' && <span> — <strong>{filterStatus === 'reorder' ? 'Needs Reorder' : 'Adequate Stock'}</strong></span>}
                </div>
            </div>

            {/* Product List */}
            {filteredAndSorted.length === 0 ? (
                <div className="card text-center" style={{ padding: 'var(--spacing-xl)' }}>
                    <h3>{searchTerm ? 'No Matching Products' : 'No Recommendations Available'}</h3>
                    <p style={{ color: 'var(--text-secondary)', marginTop: 'var(--spacing-sm)' }}>
                        {searchTerm ? 'Try a different search term' : 'Generate optimization recommendations for your products first'}
                    </p>
                </div>
            ) : viewMode === 'cards' ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(380px, 1fr))', gap: '1rem' }}>
                    {filteredAndSorted.map((rec) => {
                        const health = getStockHealth(rec);
                        const isExpanded = expandedCards.has(rec.product_id);
                        const stockRatio = rec.optimal_stock_level > 0 ? (rec.current_stock / rec.optimal_stock_level) * 100 : 0;
                        return (
                            <div key={rec.product_id} className="card" style={{ padding: '1.25rem', borderLeft: `4px solid ${health.color}`, transition: 'box-shadow 0.2s', cursor: 'pointer' }}
                                onClick={() => toggleExpand(rec.product_id)}
                                onMouseEnter={(e) => e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,0.08)'}
                                onMouseLeave={(e) => e.currentTarget.style.boxShadow = ''}>
                                {/* Header */}
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                                    <div style={{ flex: 1 }}>
                                        <div style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '0.15rem' }}>{rec.product_name}</div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)', fontFamily: 'monospace' }}>
                                            {rec.sku}
                                            {rec.category && <span style={{ marginLeft: '0.5rem', padding: '0.1rem 0.4rem', background: 'var(--bg-secondary)', borderRadius: '4px', fontFamily: 'inherit', fontSize: '0.7rem' }}>{rec.category}</span>}
                                        </div>
                                    </div>
                                    <span style={{ padding: '0.25rem 0.6rem', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 700, color: health.color, backgroundColor: health.bg, whiteSpace: 'nowrap' }}>
                                        {health.label}
                                    </span>
                                </div>
                                {/* Stock Bar */}
                                <div style={{ marginBottom: '0.75rem' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.3rem' }}>
                                        <span style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>Stock Level</span>
                                        <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>{rec.current_stock} / {rec.optimal_stock_level?.toFixed(0) || '—'}</span>
                                    </div>
                                    <div style={{ height: '6px', borderRadius: '3px', backgroundColor: 'var(--bg-secondary)', overflow: 'hidden' }}>
                                        <div style={{ height: '100%', borderRadius: '3px', backgroundColor: health.color, width: `${Math.min(stockRatio, 100)}%`, transition: 'width 0.5s ease' }} />
                                    </div>
                                </div>
                                {/* Key Metrics */}
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem', marginBottom: isExpanded ? '0.75rem' : 0 }}>
                                    <div>
                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.1rem' }}>Reorder At</div>
                                        <div style={{ fontSize: '1rem', fontWeight: 700, color: '#ea580c' }}>{rec.reorder_point?.toFixed(0) || '—'}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.1rem' }}>Order Qty</div>
                                        <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--accent-primary)' }}>{rec.economic_order_quantity?.toFixed(0) || '—'}</div>
                                    </div>
                                    <div>
                                        <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '0.1rem' }}>Savings</div>
                                        <div style={{ fontSize: '1rem', fontWeight: 700, color: '#16a34a' }}>${(rec.estimated_savings || 0).toLocaleString()}</div>
                                    </div>
                                </div>
                                {/* Expanded */}
                                {isExpanded && (
                                    <div style={{ paddingTop: '0.75rem', borderTop: '1px solid var(--border-primary)' }}>
                                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.6rem 1.5rem' }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                                <span style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>Safety Buffer</span>
                                                <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{rec.safety_stock?.toFixed(0) || '—'} units</span>
                                            </div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                                <span style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>Target Level</span>
                                                <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{rec.optimal_stock_level?.toFixed(0) || '—'} units</span>
                                            </div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                                <span style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>Current Stock</span>
                                                <span style={{ fontSize: '0.85rem', fontWeight: 600 }}>{rec.current_stock} units</span>
                                            </div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                                <span style={{ fontSize: '0.8rem', color: 'var(--text-tertiary)' }}>Reorder Point</span>
                                                <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#ea580c' }}>{rec.reorder_point?.toFixed(0) || '—'} units</span>
                                            </div>
                                        </div>
                                        {rec.needs_reorder ? (
                                            <div style={{ marginTop: '0.75rem', padding: '0.6rem 0.75rem', borderRadius: '8px', background: '#fef2f2', border: '1px solid #fecaca', fontSize: '0.82rem', color: '#991b1b', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                ⚠️ <strong>Action:</strong> Order {rec.economic_order_quantity?.toFixed(0)} units. Stock ({rec.current_stock}) below reorder point ({rec.reorder_point?.toFixed(0)}).
                                            </div>
                                        ) : (
                                            <div style={{ marginTop: '0.75rem', padding: '0.6rem 0.75rem', borderRadius: '8px', background: '#f0fdf4', border: '1px solid #bbf7d0', fontSize: '0.82rem', color: '#166534', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                ✅ Healthy. Reorder when stock drops below {rec.reorder_point?.toFixed(0)} units.
                                            </div>
                                        )}
                                    </div>
                                )}
                                <div style={{ textAlign: 'center', marginTop: '0.5rem' }}>
                                    <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>{isExpanded ? '▲ Collapse' : '▼ Details'}</span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            ) : (
                /* TABLE VIEW */
                <div className="card">
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Product</th>
                                    <th style={{ textAlign: 'center' }}>Stock</th>
                                    <th style={{ textAlign: 'center' }}>Reorder At</th>
                                    <th style={{ textAlign: 'center' }}>Safety</th>
                                    <th style={{ textAlign: 'center' }}>Order Qty</th>
                                    <th style={{ textAlign: 'center' }}>Target</th>
                                    <th style={{ textAlign: 'center' }}>Savings</th>
                                    <th style={{ textAlign: 'center' }}>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredAndSorted.map((rec) => {
                                    const health = getStockHealth(rec);
                                    return (
                                        <tr key={rec.product_id} style={{ background: rec.needs_reorder ? 'rgba(220,38,38,0.03)' : 'transparent' }}>
                                            <td>
                                                <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>{rec.product_name}</div>
                                                <div style={{ fontSize: '0.72rem', color: 'var(--text-tertiary)', fontFamily: 'monospace' }}>{rec.sku}</div>
                                            </td>
                                            <td style={{ textAlign: 'center' }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                                                    <span style={{ fontWeight: 700 }}>{rec.current_stock}</span>
                                                    <div style={{ width: '40px', height: '5px', borderRadius: '3px', backgroundColor: 'var(--bg-secondary)', overflow: 'hidden' }}>
                                                        <div style={{ height: '100%', borderRadius: '3px', backgroundColor: health.color, width: `${Math.min((rec.current_stock / (rec.optimal_stock_level || 1)) * 100, 100)}%` }} />
                                                    </div>
                                                </div>
                                            </td>
                                            <td style={{ textAlign: 'center', color: '#ea580c', fontWeight: 600 }}>{rec.reorder_point?.toFixed(0)}</td>
                                            <td style={{ textAlign: 'center' }}>{rec.safety_stock?.toFixed(0)}</td>
                                            <td style={{ textAlign: 'center', color: 'var(--accent-primary)', fontWeight: 600 }}>{rec.economic_order_quantity?.toFixed(0)}</td>
                                            <td style={{ textAlign: 'center', color: '#16a34a' }}>{rec.optimal_stock_level?.toFixed(0)}</td>
                                            <td style={{ textAlign: 'center', fontWeight: 700, color: '#16a34a' }}>${(rec.estimated_savings || 0).toLocaleString()}</td>
                                            <td style={{ textAlign: 'center' }}>
                                                <span style={{ padding: '0.25rem 0.6rem', borderRadius: '6px', fontSize: '0.75rem', fontWeight: 700, color: health.color, backgroundColor: health.bg }}>{health.label}</span>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* AI Summary */}
            <div style={{ background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)', borderRadius: '12px', padding: '1.25rem 1.5rem', marginTop: '1.5rem', borderLeft: '4px solid #4a6fa5' }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
                    <span style={{ fontSize: '1.5rem' }}>💡</span>
                    <div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.5rem', fontWeight: '600', letterSpacing: '0.5px' }}>AI OPTIMIZATION SUMMARY</div>
                        <div style={{ fontSize: '0.9rem', color: '#334155', lineHeight: '1.7' }}>
                            Analyzed <strong>{recommendations.length} products</strong> using ML-driven safety stock (z-score), EOQ, and reorder point models.
                            {needsReorder > 0 && <> <span style={{ color: '#dc2626', fontWeight: 600 }}>{needsReorder} products</span> need immediate reordering.</>}
                            {' '}Following these recommendations could save <strong style={{ color: '#16a34a' }}>${totalSavings.toLocaleString()}/year</strong>.
                        </div>
                    </div>
                </div>
            </div>

            {/* Models Modal */}
            {showModelsModal && modelsInfo && (
                <div className="modal-overlay" onClick={() => setShowModelsModal(false)}>
                    <div className="modal-content" style={{ maxWidth: '900px', maxHeight: '80vh', overflow: 'auto' }} onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>⚙️ Forecasting Models & Algorithms</h2>
                            <button className="modal-close" onClick={() => setShowModelsModal(false)}>×</button>
                        </div>
                        <div className="modal-body">
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
                            <h3 style={{ marginTop: 'var(--spacing-4)', color: 'var(--accent-primary)' }}>💰 Pricing Algorithms</h3>
                            <div style={{ background: 'var(--color-gray-50)', padding: 'var(--spacing-4)', borderRadius: '8px', marginBottom: 'var(--spacing-4)' }}>
                                <h4>{modelsInfo.pricing_algorithms.markdown.name}</h4>
                                <p>{modelsInfo.pricing_algorithms.markdown.description}</p>
                                <p><strong>Trigger:</strong> {modelsInfo.pricing_algorithms.markdown.trigger}</p>
                                <p><strong>Discount Rate:</strong> {modelsInfo.pricing_algorithms.markdown.discount_rate}</p>
                            </div>
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
