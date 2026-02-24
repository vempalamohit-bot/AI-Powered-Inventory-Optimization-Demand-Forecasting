import React, { useEffect, useState } from 'react';
import { productService, riskService } from '../services/api';

const RiskProfilerPage = () => {
    const [products, setProducts] = useState([]);
    const [selectedProductId, setSelectedProductId] = useState('');
    const [profileResult, setProfileResult] = useState(null);
    const [tradeoffs, setTradeoffs] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const loadProducts = async () => {
            try {
                const resp = await productService.getAll();
                setProducts(resp.data);
                if (resp.data.length > 0) {
                    setSelectedProductId(String(resp.data[0].id));
                }
            } catch (e) {
                console.error('Failed to load products', e);
            }
        };
        loadProducts();
    }, []);

    const runRiskProfiler = async () => {
        if (!selectedProductId) return;
        setLoading(true);
        try {
            const profileResp = await riskService.classifySku(selectedProductId, {
                customer_criticality: 'standard',
                product_lifespan_months: 12,
                supplier_reliability_pct: 90.0,
            });
            setProfileResult(profileResp.data);

            const tradeoffResp = await riskService.compareServiceLevels(selectedProductId);
            setTradeoffs(tradeoffResp.data);
        } catch (e) {
            console.error('Failed to run risk profiler', e);
            alert('Unable to calculate risk profile for this product. Ensure it has sales history.');
        } finally {
            setLoading(false);
        }
    };

    const selectedProduct = products.find(p => String(p.id) === selectedProductId);

    return (
        <div className="container" style={{ padding: 'var(--spacing-lg) var(--spacing-md)' }}>
            <h1 className="mb-3">Risk Profiler & Service Strategy</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--spacing-lg)' }}>
                Choose a product to see how different risk profiles (Conservative / Balanced / Aggressive)
                change service levels, working capital, and stockout risk.
            </p>

            <div className="grid grid-2 mb-3">
                <div className="card">
                    <h3 className="mb-2">Select Product & Run Analysis</h3>
                    <div style={{ marginBottom: 'var(--spacing-md)' }}>
                        <label htmlFor="risk-product-select">Product</label>
                        <select
                            id="risk-product-select"
                            value={selectedProductId}
                            onChange={(e) => setSelectedProductId(e.target.value)}
                            style={{
                                padding: '0.6rem',
                                fontSize: '1rem',
                                border: '2px solid #ddd',
                                borderRadius: '4px',
                                backgroundColor: '#ffffff',
                                color: '#000000',
                                fontWeight: '600',
                                width: '100%',
                            }}
                        >
                            {products.map(p => (
                                <option key={p.id} value={p.id}>
                                    {p.name} ({p.sku})
                                </option>
                            ))}
                        </select>
                    </div>

                    <button
                        className="btn btn-primary"
                        style={{ width: '100%' }}
                        onClick={runRiskProfiler}
                        disabled={loading || !selectedProductId}
                    >
                        {loading ? '⏳ Analyzing risk...' : '🧮 Analyze Risk Profile'}
                    </button>

                    {selectedProduct && (
                        <div style={{ marginTop: 'var(--spacing-lg)', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                            <p><strong>Current Stock:</strong> {selectedProduct.current_stock} units</p>
                            <p><strong>Lead Time:</strong> {selectedProduct.lead_time_days} days</p>
                            <p><strong>Unit Cost / Price:</strong> ${selectedProduct.unit_cost} / ${selectedProduct.unit_price}</p>
                        </div>
                    )}
                </div>

                <div className="card">
                    <h3 className="mb-2">What This Tool Does</h3>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                        The Risk Profiler helps your CFO and supply chain leaders decide how bold or
                        conservative to be for each SKU. It uses demand volatility, margin, product lifecycle,
                        and supplier reliability to recommend a target service level.
                    </p>
                    <ul style={{ marginTop: 'var(--spacing-md)', paddingLeft: '1.2rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
                        <li>Conservative (≈99% service) for critical or regulated items</li>
                        <li>Balanced (≈95% service) for core catalogue products</li>
                        <li>Aggressive (≈90% service) for seasonal or high-obsolescence SKUs</li>
                    </ul>
                </div>
            </div>

            {profileResult && (
                <div className="card mb-3">
                    <h3 className="mb-2">Recommended Risk Profile</h3>
                    <p style={{ fontSize: '0.95rem', marginBottom: '0.5rem' }}>
                        <strong>Profile:</strong> {profileResult.recommended_profile}
                        {' '}({profileResult.profile_target_service_level}% target service level)
                    </p>
                    <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                        <strong>Rationale:</strong> {profileResult.rationale}
                    </p>
                    <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                        <strong>Confidence Score:</strong> {profileResult.confidence_score}/100
                    </p>
                </div>
            )}

            {tradeoffs && tradeoffs.profiles && (
                <div className="card">
                    <h3 className="mb-2">Service Level Trade-offs</h3>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: 'var(--spacing-sm)' }}>
                        Compare how Conservative, Balanced, and Aggressive strategies impact inventory costs,
                        working capital, and stockout risk.
                    </p>
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>Profile</th>
                                    <th>Service Level</th>
                                    <th>Safety Stock</th>
                                    <th>EOQ</th>
                                    <th>Avg Inventory Value</th>
                                    <th>Est. Lost Margin</th>
                                </tr>
                            </thead>
                            <tbody>
                                {tradeoffs.profiles.map((p) => (
                                    <tr key={p.profile_name}>
                                        <td><strong>{p.profile_name}</strong></td>
                                        <td>{p.service_level_target}%</td>
                                        <td>{p.safety_stock}</td>
                                        <td>{p.economic_order_quantity}</td>
                                        <td>${p.average_inventory_value.toLocaleString()}</td>
                                        <td>${p.estimated_annual_lost_margin.toLocaleString()}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}
        </div>
    );
};

export default RiskProfilerPage;
