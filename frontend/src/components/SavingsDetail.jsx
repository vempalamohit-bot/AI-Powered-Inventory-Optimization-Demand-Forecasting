import React, { useEffect, useState } from 'react';
import apiService from '../services/api';
import { onRefresh } from '../services/refreshService';

const SavingsDetail = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  // Listen for data refresh events
  useEffect(() => {
    const cleanup = onRefresh((data) => {
      console.log('SavingsDetail refreshing due to:', data.source);
      fetchData();
    });
    return cleanup;
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await apiService.get('/metrics/savings-detail');
      setData(response.data);
    } catch (error) {
      console.error('Error fetching savings detail:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '40px' }}>Loading...</div>;
  }

  if (!data) {
    return <div style={{ textAlign: 'center', padding: '40px' }}>No data available</div>;
  }

  const getSavingsPercentage = (value) => {
    return ((value / data.total_annual_savings) * 100).toFixed(1);
  };

  return (
    <div>
      {/* Summary Cards */}
      <div className="detail-grid">
        <div className="detail-card">
          <div className="detail-card-label">Total Annual Savings</div>
          <div className="detail-card-value" style={{ color: '#3d6b47' }}>
            ${data.total_annual_savings.toLocaleString()}
          </div>
          <div className="detail-card-subtitle">Per year</div>
        </div>
        <div className="detail-card">
          <div className="detail-card-label">Monthly Savings</div>
          <div className="detail-card-value" style={{ color: '#7c3aed' }}>
            ${data.monthly_savings.toLocaleString()}
          </div>
          <div className="detail-card-subtitle">Average per month</div>
        </div>
        <div className="detail-card">
          <div className="detail-card-label">Daily Savings</div>
          <div className="detail-card-value" style={{ color: '#2563eb' }}>
            ${(data.total_annual_savings / 365).toFixed(2)}
          </div>
          <div className="detail-card-subtitle">Average per day</div>
        </div>
      </div>

      {/* Savings Breakdown */}
      <div className="detail-section">
        <h3>💰 Savings Breakdown by Source</h3>
        <table className="detail-table">
          <thead>
            <tr>
              <th>Savings Source</th>
              <th>Annual Amount</th>
              <th>% of Total</th>
              <th>Impact</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <strong>🏪 Reduced Holding Costs</strong>
                <div style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                  Lower inventory carrying costs through optimized stock levels
                </div>
              </td>
              <td>
                <strong style={{ color: '#3d6b47' }}>
                  ${data.breakdown.reduced_holding_costs.toLocaleString()}
                </strong>
              </td>
              <td>{getSavingsPercentage(data.breakdown.reduced_holding_costs)}%</td>
              <td>
                <div style={{ 
                  width: '100%', 
                  height: '8px', 
                  backgroundColor: '#e5e7eb', 
                  borderRadius: '4px',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    width: `${getSavingsPercentage(data.breakdown.reduced_holding_costs)}%`,
                    height: '100%',
                    backgroundColor: '#3d6b47'
                  }} />
                </div>
              </td>
            </tr>
            <tr>
              <td>
                <strong>🚨 Reduced Stockouts</strong>
                <div style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                  Prevented lost sales from better demand forecasting
                </div>
              </td>
              <td>
                <strong style={{ color: '#b84444' }}>
                  ${data.breakdown.reduced_stockouts.toLocaleString()}
                </strong>
              </td>
              <td>{getSavingsPercentage(data.breakdown.reduced_stockouts)}%</td>
              <td>
                <div style={{ 
                  width: '100%', 
                  height: '8px', 
                  backgroundColor: '#e5e7eb', 
                  borderRadius: '4px',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    width: `${getSavingsPercentage(data.breakdown.reduced_stockouts)}%`,
                    height: '100%',
                    backgroundColor: '#b84444'
                  }} />
                </div>
              </td>
            </tr>
            <tr>
              <td>
                <strong>📦 Optimized Ordering</strong>
                <div style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                  Reduced ordering frequency and improved batch sizes
                </div>
              </td>
              <td>
                <strong style={{ color: '#2563eb' }}>
                  ${data.breakdown.optimized_ordering.toLocaleString()}
                </strong>
              </td>
              <td>{getSavingsPercentage(data.breakdown.optimized_ordering)}%</td>
              <td>
                <div style={{ 
                  width: '100%', 
                  height: '8px', 
                  backgroundColor: '#e5e7eb', 
                  borderRadius: '4px',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    width: `${getSavingsPercentage(data.breakdown.optimized_ordering)}%`,
                    height: '100%',
                    backgroundColor: '#2563eb'
                  }} />
                </div>
              </td>
            </tr>
            <tr>
              <td>
                <strong>🏷️ Markdown Optimization</strong>
                <div style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                  Strategic pricing for slow-moving inventory
                </div>
              </td>
              <td>
                <strong style={{ color: '#7c3aed' }}>
                  ${data.breakdown.markdown_optimization.toLocaleString()}
                </strong>
              </td>
              <td>{getSavingsPercentage(data.breakdown.markdown_optimization)}%</td>
              <td>
                <div style={{ 
                  width: '100%', 
                  height: '8px', 
                  backgroundColor: '#e5e7eb', 
                  borderRadius: '4px',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    width: `${getSavingsPercentage(data.breakdown.markdown_optimization)}%`,
                    height: '100%',
                    backgroundColor: '#7c3aed'
                  }} />
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Category Savings */}
      <div className="detail-section">
        <h3>📊 Savings by Category</h3>
        <table className="detail-table">
          <thead>
            <tr>
              <th>Category</th>
              <th>Annual Savings</th>
              <th>Monthly Savings</th>
              <th>% of Total</th>
            </tr>
          </thead>
          <tbody>
            {data.category_savings.map((cat, idx) => (
              <tr key={idx}>
                <td><strong>{cat.category}</strong></td>
                <td>
                  <strong style={{ color: '#3d6b47' }}>
                    ${cat.savings.toLocaleString()}
                  </strong>
                </td>
                <td>${(cat.savings / 12).toFixed(2)}</td>
                <td>{((cat.savings / data.total_annual_savings) * 100).toFixed(1)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Projected Savings Timeline */}
      <div className="detail-section">
        <h3>📅 Projected Savings Timeline</h3>
        <div className="chart-container">
          <table className="detail-table">
            <thead>
              <tr>
                <th>Period</th>
                <th>Estimated Savings</th>
                <th>Cumulative</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>1 Month</strong></td>
                <td>${data.monthly_savings.toLocaleString()}</td>
                <td>${data.monthly_savings.toLocaleString()}</td>
              </tr>
              <tr>
                <td><strong>3 Months</strong></td>
                <td>${(data.monthly_savings * 3).toLocaleString()}</td>
                <td>${(data.monthly_savings * 3).toLocaleString()}</td>
              </tr>
              <tr>
                <td><strong>6 Months</strong></td>
                <td>${(data.monthly_savings * 6).toLocaleString()}</td>
                <td>${(data.monthly_savings * 6).toLocaleString()}</td>
              </tr>
              <tr style={{ backgroundColor: '#f0fdf4' }}>
                <td><strong>1 Year</strong></td>
                <td><strong>${data.total_annual_savings.toLocaleString()}</strong></td>
                <td><strong>${data.total_annual_savings.toLocaleString()}</strong></td>
              </tr>
              <tr>
                <td><strong>2 Years</strong></td>
                <td>${(data.total_annual_savings * 2).toLocaleString()}</td>
                <td>${(data.total_annual_savings * 2).toLocaleString()}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Info Box */}
      <div className="chart-container">
        <h4 style={{ marginTop: 0, color: '#1f2937' }}>💡 How We Calculate Savings</h4>
        <ul style={{ color: '#6b7280', lineHeight: '1.8', marginBottom: 0 }}>
          <li>
            <strong>Holding Costs:</strong> Reduced by maintaining optimal stock levels (25% of unit cost annually)
          </li>
          <li>
            <strong>Stockout Prevention:</strong> Avoided lost sales and customer dissatisfaction
          </li>
          <li>
            <strong>Order Optimization:</strong> Fewer orders with better batch sizes reduces processing costs
          </li>
          <li>
            <strong>Markdown Strategy:</strong> Clearing slow-moving inventory before it becomes obsolete
          </li>
        </ul>
      </div>
    </div>
  );
};

export default SavingsDetail;
