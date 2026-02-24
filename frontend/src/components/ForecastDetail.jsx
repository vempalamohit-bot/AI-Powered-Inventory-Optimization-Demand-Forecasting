import React, { useEffect, useState } from 'react';
import apiService from '../services/api';
import { onRefresh } from '../services/refreshService';

const ForecastDetail = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [backtesting, setBacktesting] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  // Listen for data refresh events
  useEffect(() => {
    const cleanup = onRefresh((data) => {
      console.log('ForecastDetail refreshing due to:', data.source);
      fetchData();
    });
    return cleanup;
  }, []);

  const fetchData = async () => {
    try {\n      setLoading(true);
      const response = await apiService.get('/metrics/forecast-detail');
      setData(response.data);
    } catch (error) {
      console.error('Error fetching forecast detail:', error);
    } finally {
      setLoading(false);
    }
  };

  const runBacktest = async () => {
    if (!confirm('This will generate historical forecasts for all products using past sales data. This may take a minute. Continue?')) {
      return;
    }

    setBacktesting(true);
    try {
      const response = await apiService.post('/analytics/backtest-forecasts');
      alert(`✅ Backtest complete!\n\n${response.data.backtested_products} products analyzed\nRefreshing accuracy data...`);
      await fetchData(); // Refresh the data
    } catch (error) {
      console.error('Error running backtest:', error);
      alert('❌ Error running backtest. Please try again.');
    } finally {
      setBacktesting(false);
    }
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '40px' }}>Loading...</div>;
  }

  if (!data) {
    return <div style={{ textAlign: 'center', padding: '40px' }}>No data available</div>;
  }

  const getAccuracyColor = (accuracy) => {
    if (accuracy >= 85) return '#3d6b47';
    if (accuracy >= 70) return '#8b6914';
    return '#b84444';
  };

  return (
    <div>
      {/* Backtest Button - Show when no data */}
      {data.total_products_analyzed === 0 && (
        <div style={{
          marginBottom: '24px',
          padding: '20px',
          background: '#FEF3C7',
          borderRadius: '12px',
          border: '2px solid #8b6914'
        }}>
          <h3 style={{ margin: '0 0 12px 0', color: '#92400e' }}>
            ⚠️ No Historical Forecast Data Available
          </h3>
          <p style={{ margin: '0 0 16px 0', color: '#78350f', lineHeight: '1.6' }}>
            To calculate forecast accuracy, we need historical forecasts to compare with actual sales. 
            Click the button below to generate historical forecasts using your past sales data (this is called "backtesting").
          </p>
          <button
            onClick={runBacktest}
            disabled={backtesting}
            style={{
              padding: '12px 24px',
              fontSize: '16px',
              fontWeight: '600',
              color: 'white',
              background: backtesting ? '#9ca3af' : '#8b6914',
              border: 'none',
              borderRadius: '8px',
              cursor: backtesting ? 'not-allowed' : 'pointer',
              boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
              transition: 'all 0.3s ease'
            }}
            onMouseEnter={(e) => {
              if (!backtesting) {
                e.target.style.transform = 'translateY(-2px)';
                e.target.style.boxShadow = '0 6px 12px rgba(0,0,0,0.15)';
              }
            }}
            onMouseLeave={(e) => {
              e.target.style.transform = 'translateY(0)';
              e.target.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
            }}
          >
            {backtesting ? '⏳ Generating Historical Forecasts...' : '🚀 Generate Historical Forecasts (Backtest)'}
          </button>
        </div>
      )}

      {/* Summary Cards */}
      <div className="detail-grid">
        <div className="detail-card">
          <div className="detail-card-label">Overall Accuracy</div>
          <div className="detail-card-value" style={{ color: getAccuracyColor(data.overall_accuracy) }}>
            {data.overall_accuracy}%
          </div>
          <div className="detail-card-subtitle">Across all products</div>
        </div>
        <div className="detail-card">
          <div className="detail-card-label">Products Analyzed</div>
          <div className="detail-card-value">{data.total_products_analyzed}</div>
          <div className="detail-card-subtitle">With sufficient data</div>
        </div>
        <div className="detail-card">
          <div className="detail-card-label">Categories</div>
          <div className="detail-card-value">{data.category_accuracy.length}</div>
          <div className="detail-card-subtitle">Being tracked</div>
        </div>
      </div>

      {/* Backtest Button - Show when there IS data (for refresh) */}
      {data.total_products_analyzed > 0 && (
        <div style={{
          marginTop: '16px',
          marginBottom: '24px',
          padding: '12px',
          background: '#f3f4f6',
          borderRadius: '8px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <span style={{ color: '#6b7280', fontSize: '14px' }}>
            💡 Want to recalculate accuracy with updated data?
          </span>
          <button
            onClick={runBacktest}
            disabled={backtesting}
            style={{
              padding: '8px 16px',
              fontSize: '14px',
              fontWeight: '600',
              color: 'white',
              background: backtesting ? '#9ca3af' : '#6366f1',
              border: 'none',
              borderRadius: '6px',
              cursor: backtesting ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s ease'
            }}
          >
            {backtesting ? '⏳ Running...' : '🔄 Regenerate Forecasts'}
          </button>
        </div>
      )}

      {/* Category Accuracy */}
      <div className="detail-section">
        <h3>📊 Forecast Accuracy by Category</h3>
        <table className="detail-table">
          <thead>
            <tr>
              <th>Category</th>
              <th>Accuracy</th>
              <th>Performance</th>
            </tr>
          </thead>
          <tbody>
            {data.category_accuracy.map((cat, idx) => (
              <tr key={idx}>
                <td><strong>{cat.category}</strong></td>
                <td>
                  <strong style={{ color: getAccuracyColor(cat.accuracy) }}>
                    {cat.accuracy}%
                  </strong>
                </td>
                <td>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '8px' 
                  }}>
                    <div style={{
                      width: '200px',
                      height: '20px',
                      backgroundColor: '#e5e7eb',
                      borderRadius: '10px',
                      overflow: 'hidden'
                    }}>
                      <div style={{
                        width: `${cat.accuracy}%`,
                        height: '100%',
                        backgroundColor: getAccuracyColor(cat.accuracy),
                        transition: 'width 0.3s ease'
                      }} />
                    </div>
                    <span>
                      {cat.accuracy >= 85 ? '🎯 Excellent' : 
                       cat.accuracy >= 70 ? '⚠️ Good' : '❌ Needs Improvement'}
                    </span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Best Forecasts */}
      <div className="detail-section">
        <h3>🎯 Top 10 Most Accurate Forecasts</h3>
        <table className="detail-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>SKU</th>
              <th>Product Name</th>
              <th>Category</th>
              <th>Accuracy</th>
            </tr>
          </thead>
          <tbody>
            {data.best_forecasts.map((product, idx) => (
              <tr key={idx} style={{ backgroundColor: idx < 3 ? '#f7faf7' : 'transparent' }}>
                <td>
                  {idx === 0 && '🥇'}
                  {idx === 1 && '🥈'}
                  {idx === 2 && '🥉'}
                  {idx > 2 && `#${idx + 1}`}
                </td>
                <td><strong>{product.sku}</strong></td>
                <td>{product.name}</td>
                <td>{product.category}</td>
                <td>
                  <strong style={{ color: getAccuracyColor(product.accuracy) }}>
                    {product.accuracy}%
                  </strong>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Worst Forecasts */}
      <div className="detail-section">
        <h3>⚠️ Products Needing Forecast Improvement</h3>
        <table className="detail-table">
          <thead>
            <tr>
              <th>SKU</th>
              <th>Product Name</th>
              <th>Category</th>
              <th>Accuracy</th>
              <th>Action Needed</th>
            </tr>
          </thead>
          <tbody>
            {data.worst_forecasts.map((product, idx) => (
              <tr key={idx} style={{ backgroundColor: '#fcf8f8' }}>
                <td><strong>{product.sku}</strong></td>
                <td>{product.name}</td>
                <td>{product.category}</td>
                <td>
                  <strong style={{ color: getAccuracyColor(product.accuracy) }}>
                    {product.accuracy}%
                  </strong>
                </td>
                <td>
                  {product.accuracy < 50 ? '🔴 Review demand patterns' :
                   product.accuracy < 70 ? '🟠 Adjust forecast model' :
                   '🟡 Monitor closely'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Info Box */}
      <div className="chart-container">
        <h4 style={{ marginTop: 0, color: '#1f2937' }}>📈 About Forecast Accuracy</h4>
        <p style={{ color: '#6b7280', lineHeight: '1.6' }}>
          Forecast accuracy is calculated using MAPE (Mean Absolute Percentage Error) comparing 
          predicted demand vs. actual sales over the past 30 days. Higher accuracy means better 
          inventory planning and reduced stockouts or overstocking.
        </p>
        <ul style={{ color: '#6b7280', lineHeight: '1.8' }}>
          <li><strong style={{ color: '#3d6b47' }}>85%+</strong>: Excellent - Highly reliable forecasts</li>
          <li><strong style={{ color: '#ea580c' }}>70-84%</strong>: Good - Minor adjustments may help</li>
          <li><strong style={{ color: '#b84444' }}>&lt;70%</strong>: Needs Improvement - Review demand patterns</li>
        </ul>
      </div>
    </div>
  );
};

export default ForecastDetail;
