import React, { useEffect, useState } from 'react';
import { analyticsService, financialService } from '../services/api';
import MetricCard from '../components/MetricCard';

const CEOActionCenter = () => {
    const [dashboard, setDashboard] = useState(null);
    const [portfolioReport, setPortfolioReport] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const load = async () => {
            try {
                const [dashResp, reportResp] = await Promise.all([
                    analyticsService.getDashboard('month'),
                    financialService.getMonthlyReport(),
                ]);
                setDashboard(dashResp.data);
                setPortfolioReport(reportResp.data);
            } catch (e) {
                console.error('Failed to load CEO Action Center data', e);
            } finally {
                setLoading(false);
            }
        };
        load();
    }, []);

    if (loading) {
        return (
            <div className="container" style={{ padding: 'var(--spacing-lg) var(--spacing-md)' }}>
                <div className="spinner" />
            </div>
        );
    }

    return (
        <div className="container" style={{ padding: 'var(--spacing-lg) var(--spacing-md)' }}>
            <h1 className="mb-3">CEO Action Center</h1>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--spacing-lg)' }}>
                High-level view of Revenue at Risk, Cash in Dead Stock, and data-driven actions
                that move margin and working capital.
            </p>

            <div className="grid grid-3 mb-4">
                <MetricCard
                    icon="💰"
                    label="Total Annualized Revenue"
                    value={portfolioReport ? `$${portfolioReport.annualized_revenue.toLocaleString()}` : '$0'}
                    gradient="primary"
                />
                <MetricCard
                    icon="🛡️"
                    label="Revenue At Risk (30d)"
                    value={`$${(dashboard?.estimated_annual_savings || 0).toLocaleString()}`}
                    gradient="danger"
                />
                <MetricCard
                    icon="📊"
                    label="Net Portfolio Benefit"
                    value={portfolioReport ? `$${portfolioReport.portfolio_impact.net_annual_portfolio_benefit.toLocaleString()}` : '$0'}
                    gradient="success"
                />
            </div>

            {portfolioReport && (
                <div className="card mb-3">
                    <h3 className="mb-2">Portfolio Financial Narrative</h3>
                    <pre style={{
                        whiteSpace: 'pre-wrap',
                        background: 'var(--bg-tertiary)',
                        padding: 'var(--spacing-md)',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.85rem',
                        lineHeight: 1.5,
                    }}>
                        {portfolioReport.portfolio_narrative}
                    </pre>
                </div>
            )}

            {portfolioReport && portfolioReport.top_opportunities && (
                <div className="card">
                    <h3 className="mb-2">Top Opportunities</h3>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: 'var(--spacing-sm)' }}>
                        Focus on these SKUs first to unlock the largest annual margin improvement.
                    </p>
                    <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Product</th>
                                    <th>Margin Saved</th>
                                    <th>Working Capital</th>
                                </tr>
                            </thead>
                            <tbody>
                                {portfolioReport.top_opportunities.map((opp, idx) => (
                                    <tr key={idx}>
                                        <td>{idx + 1}</td>
                                        <td>{opp.product_name}</td>
                                        <td>${opp.margin_saved.toLocaleString()}</td>
                                        <td>${opp.wc_required.toLocaleString()}</td>
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

export default CEOActionCenter;
