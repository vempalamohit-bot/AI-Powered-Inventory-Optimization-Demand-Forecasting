import React, { useState, useEffect } from 'react';
import { analyticsService } from '../services/api';
import { onRefresh } from '../services/refreshService';
import '../styles/MarkdownOptimizer.css';

const Optimization = () => {
    // --- MARKDOWN PRICING STATE ---
    const [opportunities, setOpportunities] = useState([]);
    const [selectedProduct, setSelectedProduct] = useState(null);
    const [analysis, setAnalysis] = useState(null);
    const [mdLoading, setMdLoading] = useState(false);
    const [mdError, setMdError] = useState(null);
    const [showModelsModal, setShowModelsModal] = useState(false);
    const [modelsInfo, setModelsInfo] = useState(null);

    useEffect(() => {
        fetchOpportunities();
    }, []);

    useEffect(() => {
        const cleanup = onRefresh(() => { fetchOpportunities(); });
        return cleanup;
    }, []);

    const loadModelsInfo = async () => {
        try {
            const response = await analyticsService.getModelsInfo();
            setModelsInfo(response.data);
            setShowModelsModal(true);
        } catch (error) {
            console.error('Error loading models info:', error);
        }
    };

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

    return (
        <div className="container" style={{ padding: 'var(--spacing-lg) var(--spacing-md)', maxWidth: '1400px', margin: '0 auto' }}>
            {/* Page Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <div>
                    <h1 style={{ fontSize: '1.75rem', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>
                        Pricing Optimizer
                    </h1>
                    <p style={{ color: 'var(--text-tertiary)', fontSize: '0.9rem' }}>
                        AI-driven markdown pricing recommendations to optimize revenue
                    </p>
                </div>
                <button className="btn btn-secondary" onClick={loadModelsInfo} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span>⚙️</span> Models Info
                </button>
            </div>

            {/* Pricing Optimizer Content */}
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
