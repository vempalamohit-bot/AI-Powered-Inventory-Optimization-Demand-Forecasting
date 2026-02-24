import React, { useEffect, useState } from 'react';
import apiService from '../services/api';
import { onRefresh } from '../services/refreshService';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';

const SalesTrendDetail = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState('30days'); // 30days, 7days, 90days

  useEffect(() => {
    fetchData();
  }, []);

  // Listen for data refresh events
  useEffect(() => {
    const cleanup = onRefresh((data) => {
      console.log('SalesTrendDetail refreshing due to:', data.source);
      fetchData();
    });
    return cleanup;
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const response = await apiService.get('/metrics/sales-trend-detail');
      setData(response.data);
    } catch (error) {
      console.error('Error fetching sales trend detail:', error);
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

  // Filter data based on view mode
  const getFilteredData = () => {
    const now = new Date();
    const days = viewMode === '7days' ? 7 : viewMode === '30days' ? 30 : 90;
    const cutoffDate = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
    return data.daily_trend.filter(d => new Date(d.date) >= cutoffDate);
  };

  const filteredData = getFilteredData();

  return (
    <div>
      {/* Summary Cards */}
      <div className="detail-grid">
        <div className="detail-card">
          <div className="detail-card-label">Revenue (Last 30 Days)</div>
          <div className="detail-card-value" style={{ color: '#3d6b47' }}>
            ${data.total_revenue_30d.toLocaleString()}
          </div>
          <div className="detail-card-subtitle">
            ${data.avg_daily_revenue_30d.toLocaleString()}/day avg
          </div>
        </div>
        <div className="detail-card">
          <div className="detail-card-label">Revenue (Last 7 Days)</div>
          <div className="detail-card-value" style={{ color: '#2563eb' }}>
            ${data.total_revenue_7d.toLocaleString()}
          </div>
          <div className="detail-card-subtitle">
            ${data.avg_daily_revenue_7d.toLocaleString()}/day avg
          </div>
        </div>
        <div className="detail-card">
          <div className="detail-card-label">Units Sold (30 Days)</div>
          <div className="detail-card-value" style={{ color: '#7c3aed' }}>
            {data.total_units_30d.toLocaleString()}
          </div>
          <div className="detail-card-subtitle">
            {Math.round(data.total_units_30d / 30)} units/day avg
          </div>
        </div>
        <div className="detail-card">
          <div className="detail-card-label">Growth Rate</div>
          <div className="detail-card-value" style={{ color: data.avg_daily_revenue_7d > data.avg_daily_revenue_30d ? '#3d6b47' : '#b84444' }}>
            {data.avg_daily_revenue_7d > data.avg_daily_revenue_30d ? '📈' : '📉'}
            {(((data.avg_daily_revenue_7d - data.avg_daily_revenue_30d) / data.avg_daily_revenue_30d) * 100).toFixed(1)}%
          </div>
          <div className="detail-card-subtitle">
            7-day vs 30-day avg
          </div>
        </div>
      </div>

      {/* Revenue Trend Chart */}
      <div className="detail-section">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ margin: 0 }}>📊 Revenue Trend</h3>
          <div>
            <button
              onClick={() => setViewMode('7days')}
              style={{
                padding: '8px 16px',
                margin: '0 4px',
                border: viewMode === '7days' ? '2px solid #4a6fa5' : '1px solid #e5e7eb',
                borderRadius: '8px',
                backgroundColor: viewMode === '7days' ? '#e8f0f8' : 'white',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: viewMode === '7days' ? '600' : '400'
              }}
            >
              7 Days
            </button>
            <button
              onClick={() => setViewMode('30days')}
              style={{
                padding: '8px 16px',
                margin: '0 4px',
                border: viewMode === '30days' ? '2px solid #4a6fa5' : '1px solid #e5e7eb',
                borderRadius: '8px',
                backgroundColor: viewMode === '30days' ? '#e8f0f8' : 'white',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: viewMode === '30days' ? '600' : '400'
              }}
            >
              30 Days
            </button>
            <button
              onClick={() => setViewMode('90days')}
              style={{
                padding: '8px 16px',
                margin: '0 4px',
                border: viewMode === '90days' ? '2px solid #4a6fa5' : '1px solid #e5e7eb',
                borderRadius: '8px',
                backgroundColor: viewMode === '90days' ? '#e8f0f8' : 'white',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: viewMode === '90days' ? '600' : '400'
              }}
            >
              90 Days
            </button>
          </div>
        </div>

        <div className="chart-container">
          <ResponsiveContainer width="100%" height={350}>
            <LineChart data={filteredData}>
              <defs>
                <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3d6b47" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#3d6b47" stopOpacity={0.1} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="date"
                stroke="#6b7280"
                style={{ fontSize: '12px' }}
                tickFormatter={(value) => new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              />
              <YAxis stroke="#6b7280" style={{ fontSize: '12px' }} />
              <Tooltip
                contentStyle={{
                  background: 'white',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                }}
                formatter={(value, name) => {
                  if (name === 'revenue') return [`$${value.toLocaleString()}`, 'Revenue'];
                  if (name === 'units') return [value.toLocaleString(), 'Units Sold'];
                  return [value, name];
                }}
                labelFormatter={(label) => new Date(label).toLocaleDateString('en-US', { 
                  weekday: 'short', 
                  month: 'short', 
                  day: 'numeric',
                  year: 'numeric'
                })}
              />
              <Line
                type="monotone"
                dataKey="revenue"
                stroke="#3d6b47"
                strokeWidth={3}
                fill="url(#revenueGradient)"
                dot={{ fill: '#3d6b47', r: 4 }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top Products by Revenue */}
      <div className="detail-section">
        <h3>💰 Top 20 Products by Revenue</h3>
        <table className="detail-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>SKU</th>
              <th>Product Name</th>
              <th>Category</th>
              <th>Units Sold</th>
              <th>Unit Price</th>
              <th>Total Revenue</th>
              <th>Avg Revenue/Day</th>
            </tr>
          </thead>
          <tbody>
            {data.top_products_by_revenue.map((product, idx) => (
              <tr key={idx} style={{ backgroundColor: idx < 5 ? '#f7faf7' : 'transparent' }}>
                <td>
                  {idx === 0 && '🥇'}
                  {idx === 1 && '🥈'}
                  {idx === 2 && '🥉'}
                  {idx > 2 && `#${idx + 1}`}
                </td>
                <td><strong>{product.sku}</strong></td>
                <td>{product.name}</td>
                <td>{product.category}</td>
                <td>{product.total_units.toLocaleString()} units</td>
                <td>${product.unit_price.toFixed(2)}</td>
                <td><strong style={{ color: '#3d6b47' }}>${product.total_revenue.toLocaleString()}</strong></td>
                <td>${(product.total_revenue / 90).toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Daily Performance Table */}
      <div className="detail-section">
        <h3>📅 Daily Performance (Recent {filteredData.length} Days)</h3>
        <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
          <table className="detail-table">
            <thead style={{ position: 'sticky', top: 0, zIndex: 10 }}>
              <tr>
                <th>Date</th>
                <th>Revenue</th>
                <th>Units Sold</th>
                <th>Avg Order Value</th>
                <th>Performance</th>
              </tr>
            </thead>
            <tbody>
              {[...filteredData].reverse().map((day, idx) => (
                <tr key={idx}>
                  <td>
                    <strong>
                      {new Date(day.date).toLocaleDateString('en-US', { 
                        weekday: 'short', 
                        month: 'short', 
                        day: 'numeric' 
                      })}
                    </strong>
                  </td>
                  <td><strong style={{ color: '#3d6b47' }}>${day.revenue.toLocaleString()}</strong></td>
                  <td>{day.units.toLocaleString()} units</td>
                  <td>${day.avg_order_value.toFixed(2)}</td>
                  <td>
                    {day.revenue > data.avg_daily_revenue_30d ? '🟢 Above Avg' :
                     day.revenue > data.avg_daily_revenue_30d * 0.8 ? '🟡 Normal' :
                     '🔴 Below Avg'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default SalesTrendDetail;
