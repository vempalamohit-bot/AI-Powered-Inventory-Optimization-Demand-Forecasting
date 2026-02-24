import { useState, useEffect } from 'react';
import { onRefresh } from '../services/refreshService';
import '../styles/MarkdownOptimizer.css';
import SampleDataCard from '../components/SampleDataCard';

export default function MarkdownOptimizerPage() {
  const [opportunities, setOpportunities] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchOpportunities();
  }, []);

  // Listen for data refresh events from Products page (upload/restock)
  useEffect(() => {
    const cleanup = onRefresh((data) => {
      console.log('Markdown Optimizer refreshing due to:', data.source);
      fetchOpportunities();
      setSelectedProduct(null);
      setAnalysis(null);
    });
    return cleanup;
  }, []);

  const fetchOpportunities = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('http://localhost:8000/api/markdown/opportunities');
      const data = await response.json();
      
      if (data.status === 'success') {
        setOpportunities(data.opportunities);
      } else {
        setError(data.message || 'Failed to fetch opportunities');
      }
    } catch (err) {
      setError(err.message || 'Error fetching opportunities');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchAnalysis = async (productId) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`http://localhost:8000/api/markdown/analyze/${productId}`);
      const data = await response.json();
      
      if (data.status === 'success') {
        setSelectedProduct(productId);
        setAnalysis(data.analysis);
      } else {
        setError(data.message || 'Failed to fetch analysis');
      }
    } catch (err) {
      setError(err.message || 'Error fetching analysis');
    } finally {
      setIsLoading(false);
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
    const colors = {
      HEALTHY: '#4caf50',
      SLOW_MOVING: '#ffc107',
      AT_RISK: '#ff6b6b',
      CRITICAL: '#ff3333'
    };
    return colors[status] || '#999';
  };

  return (
    <div className="markdown-container">
      <div className="markdown-header">
        <div style={{ maxWidth: '1600px', margin: '0 auto', padding: '0 2rem' }}>
          <h1>💰 Markdown Pricing Optimizer</h1>
          <p>Intelligent discount recommendations to maximize revenue and clear slow-moving inventory</p>
        </div>
      </div>

      {error && (
        <div className="alert alert-error">
          <span className="alert-icon">⚠️</span>
          <span>{error}</span>
        </div>
      )}

      <div className="markdown-content">
        {/* NLP Introduction Box */}
        <div style={{ 
          background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
          borderRadius: '12px',
          padding: '1.25rem 1.5rem',
          marginBottom: '1.5rem',
          borderLeft: '4px solid #4a6fa5'
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
            <span style={{ fontSize: '1.5rem' }}>💡</span>
            <div>
              <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.5rem', fontWeight: '600', letterSpacing: '0.5px' }}>
                SMART PRICING ASSISTANT
              </div>
              <div style={{ fontSize: '0.9rem', color: '#334155', lineHeight: '1.7' }}>
                <strong>What this page does:</strong> When products aren't selling fast enough, they tie up your cash and warehouse space. 
                This tool identifies items that need price adjustments and calculates the <em>optimal discount</em> — 
                not too high (losing profit), not too low (products still won't sell). 
                <strong style={{ color: '#1e40af', display: 'block', marginTop: '0.5rem' }}>
                  👉 Click any product below to see our pricing recommendation and projected financial impact.
                </strong>
              </div>
            </div>
          </div>
        </div>

        <div className="opportunities-section">
          <div className="panel-header">
            <h2>📋 Products Requiring Review ({opportunities.length})</h2>
            <button className="btn-refresh" onClick={fetchOpportunities} disabled={isLoading}>
              {isLoading ? '⏳ Loading...' : '🔄 Refresh'}
            </button>
          </div>

          {isLoading && opportunities.length === 0 ? (
            <div className="loading">⏳ Analyzing inventory...</div>
          ) : opportunities.length === 0 ? (
            <div className="no-data">✓ No markdown opportunities detected</div>
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
                    
                    {/* Mini NLP Summary */}
                    <div style={{ 
                      marginTop: '0.75rem', 
                      paddingTop: '0.75rem', 
                      borderTop: '1px solid #e5e7eb',
                      fontSize: '0.8rem',
                      color: '#64748b',
                      lineHeight: '1.5'
                    }}>
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

      {/* Modal for detailed analysis */}
      {analysis && selectedProduct && (
        <div className="modal-overlay" onClick={() => { setSelectedProduct(null); setAnalysis(null); }}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📊 Pricing Analysis & Recommendations</h2>
              <button className="btn-close-modal" onClick={() => { setSelectedProduct(null); setAnalysis(null); }}>✕</button>
            </div>

            <div className="modal-body">
              {/* Recommendation */}
              <div className="recommendation-box">
                <h3>💡 Our Recommendation</h3>
                
                {/* Executive Summary Box */}
                <div style={{ 
                  background: analysis.recommendation.recommended_discount === '0% off' 
                    ? 'linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)' 
                    : 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
                  borderRadius: '8px',
                  padding: '1rem',
                  marginBottom: '1rem',
                  borderLeft: `3px solid ${analysis.recommendation.recommended_discount === '0% off' ? '#3d6b47' : '#4a6fa5'}`
                }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
                    <span style={{ fontSize: '1.25rem' }}>{analysis.recommendation.recommended_discount === '0% off' ? '✅' : '🎯'}</span>
                    <div style={{ fontSize: '0.9rem', color: '#334155', lineHeight: '1.6' }}>
                      {analysis.recommendation.recommended_discount === '0% off' 
                        ? <>
                            <strong>Good news!</strong> {analysis.recommendation.product_name} is selling well at its current price. 
                            No discount is needed — maintain the current price of <strong>${analysis.recommendation.recommended_discount_price}</strong> for best profitability.
                          </>
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
                
                {/* NLP Context for Financial Impact */}
                <div style={{ 
                  background: 'linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%)',
                  borderRadius: '8px',
                  padding: '1rem',
                  marginBottom: '1rem',
                  borderLeft: '3px solid #3d6b47'
                }}>
                  <div style={{ fontSize: '0.85rem', color: '#064e3b', lineHeight: '1.6' }}>
                    <strong>What these numbers mean:</strong> "Revenue Gain" shows how much more you'll make compared to doing nothing 
                    (where the product may never sell). "Profit Improvement" factors in the discount cost. "Holding Cost Saved" is the 
                    warehouse and capital costs you avoid by not storing this inventory indefinitely.
                  </div>
                </div>
                
                <div className="impact-grid">
                  <div className="impact-card highlight">
                    <div className="impact-label">Revenue Gain</div>
                    <div className="impact-value" style={{ color: analysis.recommendation.financial_impact.revenue_gain_vs_do_nothing.includes('-') ? '#b84444' : '#3d6b47' }}>
                      {analysis.recommendation.financial_impact.revenue_gain_vs_do_nothing}
                    </div>
                  </div>
                  <div className="impact-card highlight">
                    <div className="impact-label">Profit Improvement</div>
                    <div className="impact-value" style={{ color: analysis.recommendation.financial_impact.profit_improvement.includes('-') ? '#b84444' : '#3d6b47' }}>
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
                
                {/* NLP Explanation for Scenarios */}
                <div style={{ 
                  background: 'linear-gradient(135deg, #fefce8 0%, #fef9c3 100%)',
                  borderRadius: '8px',
                  padding: '1rem',
                  marginBottom: '1rem',
                  borderLeft: '3px solid #8b6914'
                }}>
                  <div style={{ fontSize: '0.85rem', color: '#451a03', lineHeight: '1.6' }}>
                    <strong>How to read this table:</strong> Each row shows what happens at different discount levels. 
                    Look at the <strong>"Net Profit"</strong> column — a higher discount sells more units but at lower margins. 
                    The highlighted row is our AI's recommendation: the sweet spot that maximizes your total profit recovery.
                  </div>
                </div>
                <div className="scenarios-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Discount Level</th>
                        <th>Price</th>
                        <th>Demand Lift</th>
                        <th>Units Sold</th>
                        <th>Revenue</th>
                        <th>Net Profit</th>
                        <th>vs Current</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(analysis.recommendation.all_scenarios).map(([name, scenario]) => (
                        <tr key={name} className={name === `${parseInt(analysis.recommendation.recommended_discount)}% off` ? 'recommended' : ''}>
                          <td className="scenario-name">{name}</td>
                          <td>${scenario.markdown_price}</td>
                          <td>{scenario.demand_lift}</td>
                          <td>{scenario.units_sold}</td>
                          <td>${scenario.total_revenue.toLocaleString()}</td>
                          <td className={scenario.net_profit > 0 ? 'positive' : 'negative'}>
                            ${scenario.net_profit.toLocaleString()}
                          </td>
                          <td className={scenario.revenue_vs_no_markdown >= 0 ? 'positive' : 'negative'}>
                            ${scenario.revenue_vs_no_markdown.toLocaleString()}
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
                
                {/* NLP Explanation */}
                <div style={{ 
                  background: '#f8fafc',
                  borderRadius: '8px',
                  padding: '0.875rem',
                  marginBottom: '1rem',
                  borderLeft: '3px solid #64748b'
                }}>
                  <div style={{ fontSize: '0.85rem', color: '#475569', lineHeight: '1.6' }}>
                    <strong>Why this matters:</strong> "Days of Supply" tells you how long this stock will last at current sales velocity. 
                    Anything over 90 days is usually considered slow-moving and ties up capital that could be used elsewhere.
                  </div>
                </div>
                <div className="health-details">
                  <div className="health-item">
                    <span className="label">Health Status</span>
                    <span className="status-badge" style={{ backgroundColor: getStatusBadge(analysis.inventory_health.status) }}>
                      {analysis.inventory_health.status}
                    </span>
                  </div>
                  <div className="health-item">
                    <span className="label">Monthly Coverage</span>
                    <span className="value">{analysis.inventory_health.monthly_coverage}x months</span>
                  </div>
                  <div className="health-item">
                    <span className="label">Days of Supply</span>
                    <span className="value">{analysis.inventory_health.days_of_inventory} days</span>
                  </div>
                  <div className="health-item" style={{ gridColumn: '1 / -1' }}>
                    <span className="label">Analysis</span>
                    <span className="interpretation">{analysis.inventory_health.interpretation}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
