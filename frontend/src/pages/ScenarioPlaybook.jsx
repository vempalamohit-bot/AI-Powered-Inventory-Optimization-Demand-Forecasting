import React, { useEffect, useState } from 'react';
import { productService, scenarioService } from '../services/api';

const ScenarioPlaybook = () => {
    const [products, setProducts] = useState([]);
    const [selectedProductId, setSelectedProductId] = useState('');
    const [priceScenario, setPriceScenario] = useState(null);
    const [demandScenario, setDemandScenario] = useState(null);
    const [supplierScenario, setSupplierScenario] = useState(null);
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

    const runPriceScenario = async () => {
        if (!selectedProductId) return;
        setLoading(true);
        try {
            const payload = {
                current_price: 100,
                price_change_pct: -10,
                price_elasticity: -1.2,
                current_demand: 100,
            };
            const resp = await scenarioService.simulatePriceChange(selectedProductId, payload);
            setPriceScenario(resp.data);
        } catch (e) {
            console.error('Price scenario failed', e);
            alert('Unable to run price change scenario.');
        } finally {
            setLoading(false);
        }
    };

    const runDemandScenario = async () => {
        if (!selectedProductId) return;
        setLoading(true);
        try {
            const payload = {
                current_demand: 100,
                demand_shift_pct: 20,
                current_eoq: 200,
                current_rop: 150,
                safety_stock: 50,
                avg_daily_demand: 10,
            };
            const resp = await scenarioService.simulateDemandShift(selectedProductId, payload);
            setDemandScenario(resp.data);
        } catch (e) {
            console.error('Demand scenario failed', e);
            alert('Unable to run demand shift scenario.');
        } finally {
            setLoading(false);
        }
    };

    const runSupplierScenario = async () => {
        if (!selectedProductId) return;
        setLoading(true);
        try {
            const payload = {
                current_unit_cost: 10,
                new_unit_cost: 9,
                current_lead_time: 10,
                new_lead_time: 7,
                current_reliability: 0.9,
                new_reliability: 0.95,
                annual_demand: 1000,
            };
            const resp = await scenarioService.simulateSupplierSwitch(selectedProductId, payload);
            setSupplierScenario(resp.data);
        } catch (e) {
            console.error('Supplier scenario failed', e);
            alert('Unable to run supplier switch scenario.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="container" style={{ padding: 'var(--spacing-lg) var(--spacing-md)' }}>
            <h1 className="mb-3">Scenario Playbook</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--spacing-lg)' }}>
                Run what-if simulations for price changes, demand shifts, and supplier switches to
                understand their financial and inventory impact.
            </p>

            <div className="card mb-3">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', gap: 'var(--spacing-md)' }}>
                    <div style={{ flex: 1 }}>
                        <label htmlFor="scenario-product-select">Product</label>
                        <select
                            id="scenario-product-select"
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
                        className="btn btn-secondary"
                        disabled={loading}
                        onClick={() => { setPriceScenario(null); setDemandScenario(null); setSupplierScenario(null); }}
                    >
                        Clear Results
                    </button>
                </div>
            </div>

            <div className="grid grid-3 mb-3">
                <div className="card">
                    <h3 className="mb-2">Price Change</h3>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: 'var(--spacing-sm)' }}>
                        Simulate a 10% price decrease and see expected demand uplift and margin impact.
                    </p>
                    <button className="btn btn-primary" style={{ width: '100%' }} disabled={loading} onClick={runPriceScenario}>
                        📉 Run Price Scenario
                    </button>
                    {priceScenario && (
                        <div style={{ marginTop: 'var(--spacing-md)', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                            <p><strong>Expected Demand:</strong> {priceScenario.expected_demand}</p>
                            <p><strong>Revenue Impact:</strong> ${priceScenario.revenue_impact.toLocaleString()}</p>
                            <p><strong>Recommendation:</strong> {priceScenario.recommendation}</p>
                        </div>
                    )}
                </div>

                <div className="card">
                    <h3 className="mb-2">Demand Shift</h3>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: 'var(--spacing-sm)' }}>
                        Model a +20% demand shift and see how EOQ, ROP, and safety stock should change.
                    </p>
                    <button className="btn btn-primary" style={{ width: '100%' }} disabled={loading} onClick={runDemandScenario}>
                        📈 Run Demand Scenario
                    </button>
                    {demandScenario && (
                        <div style={{ marginTop: 'var(--spacing-md)', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                            <p><strong>New EOQ:</strong> {demandScenario.new_eoq}</p>
                            <p><strong>New ROP:</strong> {demandScenario.new_rop}</p>
                            <p><strong>Recommendation:</strong> {demandScenario.recommendation}</p>
                        </div>
                    )}
                </div>

                <div className="card">
                    <h3 className="mb-2">Supplier Switch</h3>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: 'var(--spacing-sm)' }}>
                        Evaluate switching to a cheaper/faster supplier and its effect on cost and risk.
                    </p>
                    <button className="btn btn-primary" style={{ width: '100%' }} disabled={loading} onClick={runSupplierScenario}>
                        🚚 Run Supplier Scenario
                    </button>
                    {supplierScenario && (
                        <div style={{ marginTop: 'var(--spacing-md)', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                            <p><strong>Annual Savings:</strong> ${supplierScenario.annual_savings.toLocaleString()}</p>
                            <p><strong>Service Level Impact:</strong> {supplierScenario.service_level_impact}</p>
                            <p><strong>Recommendation:</strong> {supplierScenario.recommendation}</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ScenarioPlaybook;
