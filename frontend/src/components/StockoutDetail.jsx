import React, { useEffect, useState } from 'react';
import apiService from '../services/api';
import { onRefresh } from '../services/refreshService';

const StockoutDetail = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await apiService.get('/metrics/stockout-detail');
        if (isMounted) {
          setData(response.data);
        }
      } catch (err) {
        console.error('Error fetching stockout detail:', err);
        if (isMounted) {
          setError(err.message || 'Failed to load data');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchData();
    return () => { isMounted = false; };
  }, []);

  // Listen for data refresh events
  useEffect(() => {
    const cleanup = onRefresh((data) => {
      console.log('StockoutDetail refreshing due to:', data.source);
      const fetchData = async () => {
        try {
          setLoading(true);
          const response = await apiService.get('/metrics/stockout-detail');
          setData(response.data);
        } catch (err) {
          console.error('Error refreshing stockout detail:', err);
        } finally {
          setLoading(false);
        }
      };
      fetchData();
    });
    return cleanup;
  }, []);

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '40px' }}>Loading...</div>;
  }

  if (error) {
    return <div style={{ textAlign: 'center', padding: '40px', color: '#b84444' }}>Error: {error}</div>;
  }

  if (!data) {
    return <div style={{ textAlign: 'center', padding: '40px' }}>No data available</div>;
  }

  return (
    <div>
      {/* Summary Cards */}
      <div className="detail-grid">
        <div className="detail-card">
          <div className="detail-card-label">Total At Risk</div>
          <div className="detail-card-value" style={{ color: '#b84444' }}>
            {data.total_at_risk}
          </div>
          <div className="detail-card-subtitle">Products</div>
        </div>
        <div className="detail-card">
          <div className="detail-card-label">Critical</div>
          <div className="detail-card-value" style={{ color: '#991b1b' }}>
            {data.critical_count}
          </div>
          <div className="detail-card-subtitle">&lt; 3 days stock</div>
        </div>
        <div className="detail-card">
          <div className="detail-card-label">Total Reorder Cost</div>
          <div className="detail-card-value" style={{ color: '#7c3aed' }}>
            ${data.total_reorder_cost.toLocaleString()}
          </div>
          <div className="detail-card-subtitle">For critical items</div>
        </div>
      </div>

      {/* Critical Products */}
      {data.critical_products.length > 0 && (
        <div className="detail-section">
          <h3>🚨 Critical Products (Immediate Action Required)</h3>
          <table className="detail-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Product</th>
                <th>Category</th>
                <th>Current Stock</th>
                <th>Days Left</th>
                <th>Risk</th>
                <th>Recommended Order</th>
                <th>Est. Cost</th>
              </tr>
            </thead>
            <tbody>
              {data.critical_products.map((product, idx) => (
                <tr key={idx} style={{ backgroundColor: '#fcf8f8' }}>
                  <td><strong>{product.sku}</strong></td>
                  <td>{product.name}</td>
                  <td>{product.category}</td>
                  <td>{product.current_stock} units</td>
                  <td><strong style={{ color: '#b84444' }}>{product.days_until_stockout} days</strong></td>
                  <td>
                    <span className={`risk-badge ${product.risk_level.toLowerCase()}`}>
                      {product.risk_level}
                    </span>
                  </td>
                  <td><strong>{product.recommended_order_qty} units</strong></td>
                  <td>${(product.recommended_order_qty * product.unit_cost).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* All At-Risk Products */}
      <div className="detail-section">
        <h3>⚠️ All At-Risk Products (Top 20 Most Urgent)</h3>
        <table className="detail-table">
          <thead>
            <tr>
              <th>SKU</th>
              <th>Product</th>
              <th>Category</th>
              <th>Current Stock</th>
              <th>Days Until Stockout</th>
              <th>Risk Level</th>
              <th>Avg Daily Demand</th>
              <th>Reorder Point</th>
              <th>Recommended Order</th>
              <th>Lead Time</th>
            </tr>
          </thead>
          <tbody>
            {data.at_risk_products.map((product, idx) => (
              <tr key={idx}>
                <td><strong>{product.sku}</strong></td>
                <td>{product.name}</td>
                <td>{product.category}</td>
                <td>{product.current_stock} units</td>
                <td>
                  <strong style={{ 
                    color: product.days_until_stockout < 7 ? '#b84444' : '#b86c30' 
                  }}>
                    {product.days_until_stockout} days
                  </strong>
                </td>
                <td>
                  <span className={`risk-badge ${product.risk_level.toLowerCase()}`}>
                    {product.risk_level}
                  </span>
                </td>
                <td>{product.average_daily_demand} units/day</td>
                <td>{product.reorder_point} units</td>
                <td><strong>{product.recommended_order_qty} units</strong></td>
                <td>{product.lead_time_days} days</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.total_at_risk === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">✅</div>
          <div className="empty-state-text">
            Great! No products are at risk of stockout.
          </div>
        </div>
      )}
    </div>
  );
};

export default StockoutDetail;
