import React, { useState, useEffect, useMemo } from 'react';
import { optimizationService, analyticsService } from '../services/api';
import { onRefresh } from '../services/refreshService';
import { frontendCache } from '../services/cache';
import '../styles/MarkdownOptimizer.css';

const Optimization = () => {
    const [activeTab, setActiveTab] = useState('inventory');

    // --- INVENTORY OPTIMIZATION STATE ---
    const [recommendations, setRecommendations] = useState([]);
    const [invLoading, setInvLoading] = useState(true);
    const [showModelsModal, setShowModelsModal] = useState(false);
    const [modelsInfo, setModelsInfo] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [sortBy, setSortBy] = useState('savings');
    const [filterStatus, setFilterStatus] = useState('all');
    const [expandedCards, setExpandedCards] = useState(new Set());
    const [viewMode, setViewMode] = useState('cards');

    // --- MARKDOWN PRICING STATE ---
    const [opportunities, setOpportunities] = useState([]);
    const [selectedProduct, setSelectedProduct] = useState(null);
    const [analysis, setAnalysis] = useState(null);
    const [mdLoading, setMdLoading] = useState(false);
    const [mdError, setMdError] = useState(null);

    useEffect(() => {
        loadRecommendations();
        fetchOpportunities();
    }, []);

    useEffect(() => {
        const cleanup = onRefresh(() => {
            loadRecommendations();
            fetchOpportunities();
        });
        return cleanup;
    }, []);

    // ===== INVENTORY OPTIMIZATION FUNCTIONS =====
    const loadRecommendations = async () => {
        try {
            const cacheKey = 'recommendations';
            const cached = frontendCache.get(cacheKey, 60);
            if (cached) {
                setRecommendations(cached);
                setInvLoading(false);
                return;
            }
            const response = await optimizationService.getAll();
            setRecommendations(response.data);
            frontendCache.set(cacheKey, response.data);
        } catch (error) {
            console.error('Error loading recommendations:', error);
        } finally {
            setInvLoading(false);
        }
    };

    const loadModelsInfo = async () => {
        try {
            const response = await analyticsService.getModelsInfo();
            setModelsInfo(response.data);
            setShowModelsModal(true);
        } catch (error) {
            console.error('Error loading models info:', error);
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

    // ===== MARKDOWN PRICING FUNCTIONS =====
    const fetchOpportunities = async () => {
        setMdLoading(true);
        setMdError(null);
        try {
            const response = await fetch('http://localhost:8000/api/markdown/opportunities');
            const data = await response.json();
            if (data.status === 'success') {
                setOpportunities(data.opportunities);
            } else {
                setMdError(data.message || 'Failed to fetch opportunities');
            }
        } catch (err) {
            setMdError(err.message || 'Error fetching opportunities');
        } finally {
            setMdLoading(false);
        }
    };

    const fetchAnalysis = async (productId) => {
        setMdLoading(true);
        setMdError(null);
        try {
            const response = await fetch(`http://localhost:8000/api/markdown/analyze/${productId}`);
            const data = await response.json();
            if (data.status === 'success') {
                setSelectedProduct(productId);
                setAnalysis(data.analysis);
            } else {
                setMdError(data.message || 'Failed to fetch analysis');
            }
        } catch (err) {
            setMdError(err.message || 'Error fetching analysis');
        } finally {
            setMdLoading(false);
        }
    };

    const getUrgencyColor = (urgency) => {
        if (urgency.includes('IMMEDIATE')) return '#ff3333';
        if (urgency.includes('URGENT')) return '#ff6b6b';
        if (urgency.includes('HIGH')) return '#ffa500';
        if (urgency.includes('MEDIUM')) return '#ffc107';
        return '#4caf50';
    };

    const getStatusBadge = (status) => {
        const colors = { HEALTHY: '#4caf50', SLOW_MOVING: '#ffc107', AT_RISK: '#ff6b6b', CRITICAL: '#ff3333' };
        return colors[status] || '#999';
    };

    // ===== TAB STYLES =====
    const tabStyle = (isActive) => ({
        padding: '0.75rem 1.5rem',
        fontSize: '0.95rem',
        fontWeight: isActive ? 700 : 500,
        color: isActive ? '#fff' : 'var(--text-secondary)',
        backgroundColor: isActive ? 'var(--accent-primary)' : 'transparent',
        border: isActive ? 'none' : '1px solid var(--border-primary)',
        borderRadius: '8px',
        cursor: 'pointer',
        transition: 'all 0.2s',
        display: 'flex',
        alignItems: 'center',
        gap: '0.5rem'
    });

    return (
        <div className="container" style={{ padding: 'var(--spacing-lg) var(--spacing-md)', maxWidth: '1400px', margin: '0 auto' }}>
            {/* Page Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <div>
                    <h1 style={{ fontSize: '1.75rem', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                        Optimization
                    </h1>
                    <p style={{ color: 'var(--text-tertiary)', fontSize: '0.9rem' }}>
                        AI-driven inventory reorder optimization and markdown pricing recommendations
                    </p>
                </div>
                <button className="btn btn-secondary" onClick={loadModelsInfo} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span>⚙️</span> Models Info
                </button>
            </div>

            {/* Tab Selector */}
            <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.5rem', borderBottom: '2px solid var(--border-primary)', paddingBottom: '0.75rem' }}>
                <button style={tabStyle(activeTab === 'inventory')} onClick={() => setActiveTab('inventory')}>
                    📦 Inventory Optimization
                    {needsReorder > 0 && <span style={{ background: '#dc2626', color: '#fff', borderRadius: '10px', padding: '0.1rem 0.5rem', fontSize: '0.75rem', fontWeight: 700 }}>{needsReorder}</span>}
                </button>
                <button style={tabStyle(activeTab === 'pricing')} onClick={() => setActiveTab('pricing')}>
                    💰 Pricing Optimizer
                    {opportunities.length > 0 && <span style={{ background: '#ea580c', color: '#fff', borderRadius: '10px', padding: '0.1rem 0.5rem', fontSize: '0.75rem', fontWeight: 700 }}>{opportunities.length}</span>}
                </button>
            </div>

            {/* ===== INVENTORY OPTIMIZATION TAB ===== */}
            {activeTab === 'inventory' && (
                <>
                    {invLoading ? (
                        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '300px' }}><div className="spinner"></div></div>
                    ) : (
                        <>
                            {/* Summary Cards */}
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

                            {/* Cards or Table View */}
                            {filteredAndSorted.length === 0 ? (
                                <div className="card text-center" style={{ padding: 'var(--spacing-xl)' }}>
                                    <h3>{searchTerm ? 'No Matching Products' : 'No Recommendations Available'}</h3>
                                    <p style={{ color: 'var(--text-secondary)', marginTop: 'var(--spacing-sm)' }}>
                                        {searchTerm ? 'Try a different search term' : 'Generate optimization recommendations first'}
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
                                                {/* Expanded Details */}
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
                        </>
                    )}
                </>
            )}

            {/* ===== PRICING OPTIMIZER TAB ===== */}
            {activeTab === 'pricing' && (
                <div className="markdown-container" style={{ padding: 0 }}>
                    {/* Intro Box */}
                    <div style={{ background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)', borderRadius: '12px', padding: '1.25rem 1.5rem', marginBottom: '1.5rem', borderLeft: '4px solid #4a6fa5' }}>
                        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
                            <span style={{ fontSize: '1.5rem' }}>💡</span>
                            <div>
                                <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.5rem', fontWeight: '600', letterSpacing: '0.5px' }}>SMART PRICING ASSISTANT</div>
                                <div style={{ fontSize: '0.9rem', color: '#334155', lineHeight: '1.7' }}>
                                    <strong>What this does:</strong> When products aren't selling fast enough, they tie up cash and warehouse space.
                                    This tool identifies items needing price adjustments and calculates the <em>optimal discount</em> —
                                    not too high (losing profit), not too low (products still won't sell).
                                    <strong style={{ color: '#1e40af', display: 'block', marginTop: '0.5rem' }}>
                                        👉 Click any product below to see our pricing recommendation and projected financial impact.
                                    </strong>
                                </div>
                            </div>
                        </div>
                    </div>

                    {mdError && (
                        <div className="alert alert-error" style={{ marginBottom: '1rem' }}>
                            <span>⚠️</span> <span>{mdError}</span>
                        </div>
                    )}

                    <div className="opportunities-section">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                            <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>📋 Products Requiring Review ({opportunities.length})</h2>
                            <button className="btn btn-secondary" onClick={fetchOpportunities} disabled={mdLoading} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                {mdLoading ? '⏳ Loading...' : '🔄 Refresh'}
                            </button>
                        </div>

                        {mdLoading && opportunities.length === 0 ? (
                            <div style={{ display: 'flex', justifyContent: 'center', minHeight: '200px', alignItems: 'center' }}><div className="spinner"></div></div>
                        ) : opportunities.length === 0 ? (
                            <div className="card text-center" style={{ padding: 'var(--spacing-xl)' }}>
                                <h3>✓ No markdown opportunities detected</h3>
                                <p style={{ color: 'var(--text-secondary)' }}>All products are selling at a healthy pace.</p>
                            </div>
                        ) : (
                            <div className="opportunities-grid">
                                {opportunities.map((opp) => (
                                    <div
                                        key={opp.product_id}
                                        className="opportunity-card"
                                        onClick={() => fetchAnalysis(opp.product_id)}
                                        style={{ borderTopColor: getUrgencyColor(opp.timing.markdown_urgency) }}
                                    >
                                        <div className="opportunity-header">
                                            <div className="product-info">
                                                <h3>{opp.name}</h3>
                                                <p className="sku">SKU: {opp.sku}</p>
                                            </div>
                                            <div className="urgency-badge" style={{ backgroundColor: getUrgencyColor(opp.timing.markdown_urgency) }}>
                                                {opp.timing.markdown_urgency}
                                            </div>
                                        </div>
                                        <div className="opportunity-details">
                                            <div className="detail-row">
                                                <span className="label">Current Stock:</span>
                                                <span className="value">{opp.current_stock} units</span>
                                            </div>
                                            <div className="detail-row">
                                                <span className="label">Days of Inventory:</span>
                                                <span className="value">{opp.health.days_of_inventory} days</span>
                                            </div>
                                            <div className="detail-row">
                                                <span className="label">Health Status:</span>
                                                <span className="status-badge" style={{ backgroundColor: getStatusBadge(opp.health.status) }}>
                                                    {opp.health.status}
                                                </span>
                                            </div>
                                            <div className="detail-row">
                                                <span className="label">Start Markdown In:</span>
                                                <span className="value" style={{ fontWeight: 'bold', color: getUrgencyColor(opp.timing.markdown_urgency) }}>
                                                    {opp.timing.days_until_markdown} days
                                                </span>
                                            </div>
                                            <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid #e5e7eb', fontSize: '0.8rem', color: '#64748b', lineHeight: '1.5' }}>
                                                {opp.health.days_of_inventory > 120
                                                    ? `⚠️ This product has ${Math.round(opp.health.days_of_inventory / 30)} months of stock — consider discounting soon.`
                                                    : opp.health.days_of_inventory > 90
                                                        ? `📦 Stock levels are elevated. Click for optimal discount recommendation.`
                                                        : `✓ Inventory is manageable. Review for optimization opportunities.`
                                                }
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* ===== PRICING ANALYSIS MODAL ===== */}
            {analysis && selectedProduct && (
                <div className="modal-overlay" onClick={() => { setSelectedProduct(null); setAnalysis(null); }}>
                    <div className="modal-content" style={{ maxWidth: '900px', maxHeight: '80vh', overflow: 'auto' }} onClick={(e) => e.stopPropagation()}>
                        <div className="modal-header">
                            <h2>📊 Pricing Analysis & Recommendations</h2>
                            <button className="modal-close" onClick={() => { setSelectedProduct(null); setAnalysis(null); }}>×</button>
                        </div>
                        <div className="modal-body">
                            {/* Recommendation */}
                            <div className="recommendation-box">
                                <h3>💡 Our Recommendation</h3>
                                <div style={{ background: analysis.recommendation.recommended_discount === '0% off' ? 'linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)' : 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)', borderRadius: '8px', padding: '1rem', marginBottom: '1rem', borderLeft: `3px solid ${analysis.recommendation.recommended_discount === '0% off' ? '#3d6b47' : '#4a6fa5'}` }}>
                                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                                        <span style={{ fontSize: '1.25rem' }}>{analysis.recommendation.recommended_discount === '0% off' ? '✅' : '🎯'}</span>
                                        <div style={{ fontSize: '0.9rem', color: '#334155', lineHeight: '1.6' }}>
                                            {analysis.recommendation.recommended_discount === '0% off'
                                                ? <><strong>Good news!</strong> {analysis.recommendation.product_name} is selling well at its current price. No discount is needed — maintain the current price of <strong>${analysis.recommendation.recommended_discount_price}</strong> for best profitability.</>
                                                : analysis.recommendation.executive_summary
                                            }
                                        </div>
                                    </div>
                                </div>
                                <div className="financial-impact">
                                    <div className="impact-item">
                                        <span className="label">Recommended Discount:</span>
                                        <span className="value" style={{ fontSize: '1.3em', fontWeight: 'bold', color: analysis.recommendation.recommended_discount === '0% off' ? '#3d6b47' : '#1f2937' }}>
                                            {analysis.recommendation.recommended_discount === '0% off' ? 'No discount needed' : analysis.recommendation.recommended_discount}
                                        </span>
                                    </div>
                                    <div className="impact-item">
                                        <span className="label">New Price:</span>
                                        <span className="value">${analysis.recommendation.recommended_discount_price}</span>
                                    </div>
                                    <div className="impact-item">
                                        <span className="label">Units to Clear:</span>
                                        <span className="value">{analysis.recommendation.financial_impact.units_to_clear} units</span>
                                    </div>
                                    <div className="impact-item">
                                        <span className="label">Clearance Rate:</span>
                                        <span className="value">{analysis.recommendation.financial_impact.clearance_rate}</span>
                                    </div>
                                </div>
                            </div>

                            {/* Financial Impact */}
                            <div className="financial-box">
                                <h3>💰 Projected Financial Impact</h3>
                                <div style={{ background: 'linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)', borderRadius: '8px', padding: '1rem', marginBottom: '1rem', borderLeft: '3px solid #3d6b47' }}>
                                    <div style={{ fontSize: '0.85rem', color: '#064e3b', lineHeight: '1.6' }}>
                                        <strong>What these numbers mean:</strong> "Revenue Gain" shows how much more you'll make compared to doing nothing.
                                        "Profit Improvement" factors in the discount cost. "Holding Cost Saved" is the warehouse and capital costs avoided.
                                    </div>
                                </div>
                                <div className="impact-grid">
                                    <div className="impact-card highlight">
                                        <div className="impact-label">Revenue Gain</div>
                                        <div className="impact-value" style={{ color: analysis.recommendation.financial_impact.revenue_gain_vs_do_nothing?.includes('-') ? '#b84444' : '#3d6b47' }}>
                                            {analysis.recommendation.financial_impact.revenue_gain_vs_do_nothing}
                                        </div>
                                    </div>
                                    <div className="impact-card highlight">
                                        <div className="impact-label">Profit Improvement</div>
                                        <div className="impact-value" style={{ color: analysis.recommendation.financial_impact.profit_improvement?.includes('-') ? '#b84444' : '#3d6b47' }}>
                                            {analysis.recommendation.financial_impact.profit_improvement}
                                        </div>
                                    </div>
                                    <div className="impact-card">
                                        <div className="impact-label">Holding Cost Saved</div>
                                        <div className="impact-value" style={{ color: '#4a6fa5' }}>
                                            {analysis.recommendation.financial_impact.inventory_holding_cost_saved}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Scenario Comparison */}
                            <div className="scenarios-box">
                                <h3>📈 Pricing Scenario Analysis</h3>
                                <div style={{ background: 'linear-gradient(135deg, #fefce8 0%, #fef9c3 100%)', borderRadius: '8px', padding: '1rem', marginBottom: '1rem', borderLeft: '3px solid #8b6914' }}>
                                    <div style={{ fontSize: '0.85rem', color: '#451a03', lineHeight: '1.6' }}>
                                        <strong>How to read this table:</strong> Each row shows what happens at different discount levels.
                                        The highlighted row is the AI's recommendation — the sweet spot that maximizes total profit recovery.
                                    </div>
                                </div>
                                <div className="scenarios-table">
                                    <table>
                                        <thead>
                                            <tr>
                                                <th>Discount</th>
                                                <th>Price</th>
                                                <th>Demand Lift</th>
                                                <th>Units Sold</th>
                                                <th>Revenue</th>
                                                <th>Net Profit</th>
                                                <th>vs Current</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {analysis.recommendation.all_scenarios && Object.entries(analysis.recommendation.all_scenarios).map(([name, scenario]) => (
                                                <tr key={name} className={name === `${parseInt(analysis.recommendation.recommended_discount)}% off` ? 'recommended' : ''}>
                                                    <td className="scenario-name">{name}</td>
                                                    <td>${scenario.markdown_price}</td>
                                                    <td>{scenario.demand_lift}</td>
                                                    <td>{scenario.units_sold}</td>
                                                    <td>${scenario.total_revenue?.toLocaleString()}</td>
                                                    <td className={scenario.net_profit > 0 ? 'positive' : 'negative'}>
                                                        ${scenario.net_profit?.toLocaleString()}
                                                    </td>
                                                    <td className={scenario.revenue_vs_no_markdown >= 0 ? 'positive' : 'negative'}>
                                                        ${scenario.revenue_vs_no_markdown?.toLocaleString()}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            {/* Inventory Health */}
                            <div className="health-box">
                                <h3>📦 Current Inventory Status</h3>
                                <div className="health-details">
                                    <div className="health-item">
                                        <span className="label">Health Status</span>
                                        <span className="status-badge" style={{ backgroundColor: getStatusBadge(analysis.inventory_health?.status) }}>
                                            {analysis.inventory_health?.status}
                                        </span>
                                    </div>
                                    <div className="health-item">
                                        <span className="label">Monthly Coverage</span>
                                        <span className="value">{analysis.inventory_health?.monthly_coverage}x months</span>
                                    </div>
                                    <div className="health-item">
                                        <span className="label">Days of Supply</span>
                                        <span className="value">{analysis.inventory_health?.days_of_inventory} days</span>
                                    </div>
                                    <div className="health-item" style={{ gridColumn: '1 / -1' }}>
                                        <span className="label">Analysis</span>
                                        <span className="interpretation">{analysis.inventory_health?.interpretation}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

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
                                <h4>{modelsInfo.forecasting_models?.primary?.name}</h4>
                                <p><strong>Library:</strong> {modelsInfo.forecasting_models?.primary?.library}</p>
                                <p>{modelsInfo.forecasting_models?.primary?.description}</p>
                                <h4 style={{ marginTop: 'var(--spacing-3)' }}>{modelsInfo.forecasting_models?.secondary?.name}</h4>
                                <p><strong>Library:</strong> {modelsInfo.forecasting_models?.secondary?.library}</p>
                                <p>{modelsInfo.forecasting_models?.secondary?.description}</p>
                                <div style={{ background: '#E0F2FE', padding: 'var(--spacing-3)', borderRadius: '6px', marginTop: 'var(--spacing-3)' }}>
                                    <h4>🎯 {modelsInfo.forecasting_models?.ensemble?.name}</h4>
                                    <p>{modelsInfo.forecasting_models?.ensemble?.description}</p>
                                </div>
                            </div>
                            <h3 style={{ color: 'var(--accent-primary)' }}>⚙️ Optimization Algorithms</h3>
                            <div style={{ background: 'var(--color-gray-50)', padding: 'var(--spacing-4)', borderRadius: '8px', marginBottom: 'var(--spacing-4)' }}>
                                {modelsInfo.optimization_algorithms && Object.entries(modelsInfo.optimization_algorithms).map(([key, algo]) => (
                                    <div key={key} style={{ marginBottom: 'var(--spacing-3)', paddingBottom: 'var(--spacing-3)', borderBottom: '1px solid var(--border-color)' }}>
                                        <h4>{algo.name}</h4>
                                        <p><strong>Type:</strong> {algo.type}</p>
                                        <p><strong>Formula:</strong> <code style={{ background: '#FEF3C7', padding: '2px 8px', borderRadius: '4px' }}>{algo.formula}</code></p>
                                        <p>{algo.description}</p>
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
