import React, { useEffect, useState } from 'react';
import apiService from '../services/api';

const ProductInsightModal = ({ productId, productSku }) => {
  const [data, setData] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showForecast, setShowForecast] = useState(false);

  useEffect(() => {
    if (productId) {
      fetchData();
    }
  }, [productId]);

  const fetchData = async () => {
    try {
      const [recommendationsResponse, forecastResponse] = await Promise.all([
        apiService.get(`/products/${productId}/recommendations`),
        apiService.get(`/products/${productId}/forecast-comparison`)
      ]);
      setData(recommendationsResponse.data);
      setForecastData(forecastResponse.data);
    } catch (error) {
      console.error('Error fetching product insights:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 40px' }}>
        <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>🔄</div>
        <div style={{ color: '#64748b', fontSize: '0.95rem' }}>Analyzing product data...</div>
      </div>
    );
  }

  if (!data || data.error) {
    return (
      <div style={{ textAlign: 'center', padding: '60px 40px' }}>
        <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>📭</div>
        <div style={{ color: '#64748b' }}>No data available for this product</div>
      </div>
    );
  }

  // Calculate key metrics
  const profitPerUnit = data.product.unit_price - data.product.unit_cost;
  const recommendedOrder = Math.max(data.metrics.reorder_point * 2, Math.ceil(data.metrics.average_daily_demand * 30));
  const orderCost = recommendedOrder * data.product.unit_cost;
  const potentialProfit = recommendedOrder * profitPerUnit;
  const monthlyProfit = profitPerUnit * data.metrics.average_daily_demand * 30;
  const holdingCost = data.product.current_stock * data.product.unit_cost * 0.25;
  const isLowStock = data.product.current_stock <= data.metrics.reorder_point;
  const isUrgent = data.metrics.days_until_stockout < 7;
  const isSlowMoving = data.metrics.average_daily_demand < 1 && data.product.current_stock > 100;

  // Get status
  const getStatus = () => {
    if (data.metrics.risk_level === 'HIGH') return { label: 'CRITICAL', color: '#b84444', bg: '#fef2f2' };
    if (data.metrics.risk_level === 'MEDIUM') return { label: 'ATTENTION', color: '#8b6914', bg: '#fefce8' };
    return { label: 'HEALTHY', color: '#3d6b47', bg: '#f0fdf4' };
  };
  const status = getStatus();

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, sans-serif' }}>
      {/* Product Header - Clean & Simple */}
      <div style={{
        background: '#f8fafc',
        border: '1px solid #e2e8f0',
        borderRadius: '8px',
        padding: '1.5rem',
        marginBottom: '1.5rem'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2 style={{ margin: '0 0 0.75rem 0', color: '#1e293b', fontSize: '1.5rem', fontWeight: '600' }}>
              {data.product.name}
            </h2>
            <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.85rem', color: '#64748b' }}>
              <span><strong>SKU:</strong> {data.product.sku}</span>
              <span><strong>Category:</strong> {data.product.category}</span>
              <span><strong>Stock:</strong> {data.product.current_stock} units</span>
              <span><strong>Margin:</strong> {data.product.profit_margin}%</span>
            </div>
          </div>
          <div style={{
            padding: '0.5rem 1rem',
            background: status.bg,
            border: `1px solid ${status.color}`,
            borderRadius: '6px',
            textAlign: 'center'
          }}>
            <div style={{ fontSize: '0.7rem', color: '#64748b', marginBottom: '0.25rem' }}>STATUS</div>
            <div style={{ color: status.color, fontWeight: '700', fontSize: '1rem' }}>{status.label}</div>
          </div>
        </div>
      </div>

      {/* Summary - NLP Style */}
      <div style={{
        background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
        borderRadius: '8px',
        padding: '1.25rem',
        marginBottom: '1.5rem',
        borderLeft: `3px solid ${status.color}`
      }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
          <span style={{ fontSize: '1.25rem' }}>💡</span>
          <div>
            <div style={{ fontSize: '0.7rem', color: '#64748b', marginBottom: '0.5rem', fontWeight: '600' }}>
              EXECUTIVE SUMMARY
            </div>
            <div style={{ fontSize: '0.9rem', color: '#334155', lineHeight: '1.7' }}>
              {isLowStock ? (
                <>
                  <strong>Action needed:</strong> Your stock of <strong>{data.product.name}</strong> is currently at{' '}
                  <strong>{data.product.current_stock} units</strong>, which is below your reorder point of{' '}
                  <strong>{data.metrics.reorder_point} units</strong>. Based on your average sales of{' '}
                  <strong>{Math.round(data.metrics.average_daily_demand)} units/day</strong>, you have approximately{' '}
                  <strong style={{ color: isUrgent ? '#b84444' : '#8b6914' }}>
                    {data.metrics.days_until_stockout} days
                  </strong>{' '}
                  until stockout. We recommend ordering <strong>{recommendedOrder} units</strong>{' '}
                  (approximately ${orderCost.toLocaleString()}) to cover the next 30 days of demand plus safety stock.
                </>
              ) : isSlowMoving ? (
                <>
                  <strong>Opportunity:</strong> This product is moving slowly at{' '}
                  <strong>{Math.round(data.metrics.average_daily_demand)} units/day</strong> with{' '}
                  <strong>{data.product.current_stock} units</strong> in stock. At this rate, it would take{' '}
                  <strong>{Math.ceil(data.product.current_stock / (data.metrics.average_daily_demand || 0.1))} days</strong>{' '}
                  to sell through. Consider a <strong>promotional markdown</strong> to improve cash flow and reduce{' '}
                  holding costs (currently <strong>${holdingCost.toFixed(2)}/year</strong>).
                </>
              ) : (
                <>
                  <strong>Status healthy:</strong> Your inventory of <strong>{data.product.name}</strong> is in good shape with{' '}
                  <strong>{data.product.current_stock} units</strong> on hand. This gives you approximately{' '}
                  <strong style={{ color: '#3d6b47' }}>{data.metrics.days_until_stockout} days</strong> of coverage{' '}
                  at current demand levels ({Math.round(data.metrics.average_daily_demand)} units/day). Your profit margin of{' '}
                  <strong>{data.product.profit_margin}%</strong> is{' '}
                  {data.product.profit_margin > 40 ? 'excellent' : data.product.profit_margin > 20 ? 'healthy' : 'below target'}.
                  {data.metrics.days_until_stockout < 21 && (
                    <> Plan to reorder within <strong>{Math.max(0, data.metrics.days_until_stockout - (data.metrics.lead_time_days || 7))} days</strong> to maintain stock levels.</>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Key Metrics Table */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ fontSize: '1rem', color: '#1e293b', marginBottom: '1rem', fontWeight: '600' }}>
          📊 Key Performance Indicators
        </h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
          <tbody>
            <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={{ padding: '0.75rem 1rem', color: '#64748b', width: '40%' }}>Current Stock</td>
              <td style={{ padding: '0.75rem 1rem', fontWeight: '600', color: isLowStock ? '#b84444' : '#1e293b' }}>
                {data.product.current_stock} units {isLowStock && <span style={{ fontSize: '0.75rem' }}>(Below reorder point)</span>}
              </td>
            </tr>
            <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={{ padding: '0.75rem 1rem', color: '#64748b' }}>Reorder Point</td>
              <td style={{ padding: '0.75rem 1rem', fontWeight: '600', color: '#1e293b' }}>{data.metrics.reorder_point} units</td>
            </tr>
            <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={{ padding: '0.75rem 1rem', color: '#64748b' }}>Average Daily Demand</td>
              <td style={{ padding: '0.75rem 1rem', fontWeight: '600', color: '#1e293b' }}>{Math.round(data.metrics.average_daily_demand)} units/day</td>
            </tr>
            <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={{ padding: '0.75rem 1rem', color: '#64748b' }}>Days Until Stockout</td>
              <td style={{ padding: '0.75rem 1rem', fontWeight: '600', color: isUrgent ? '#b84444' : data.metrics.days_until_stockout < 14 ? '#8b6914' : '#3d6b47' }}>
                {data.metrics.days_until_stockout} days
              </td>
            </tr>
            <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={{ padding: '0.75rem 1rem', color: '#64748b' }}>Lead Time</td>
              <td style={{ padding: '0.75rem 1rem', fontWeight: '600', color: '#1e293b' }}>{data.metrics.lead_time_days || 'N/A'} days</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Recommendations - Clean List Format */}
      {data.recommendations.length > 0 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1rem', color: '#1e293b', marginBottom: '1rem', fontWeight: '600' }}>
            🎯 Suggestions ({data.recommendations.length})
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {data.recommendations.map((rec, idx) => {
              const priorityColors = {
                critical: { color: '#b84444', bg: '#fef2f2', border: '#fecaca' },
                high: { color: '#b86c30', bg: '#fff7ed', border: '#fed7aa' },
                medium: { color: '#8b6914', bg: '#fefce8', border: '#fef08a' },
                low: { color: '#4a6fa5', bg: '#eff6ff', border: '#bfdbfe' }
              };
              const pStyle = priorityColors[rec.priority] || priorityColors.medium;
              
              return (
                <div key={idx} style={{
                  background: '#fff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '8px',
                  overflow: 'hidden'
                }}>
                  {/* Priority Header */}
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '0.75rem 1rem',
                    background: pStyle.bg,
                    borderBottom: `1px solid ${pStyle.border}`
                  }}>
                    <div style={{ fontWeight: '600', color: '#1e293b' }}>{rec.title}</div>
                    <span style={{
                      padding: '0.25rem 0.5rem',
                      background: pStyle.color,
                      color: '#fff',
                      borderRadius: '4px',
                      fontSize: '0.7rem',
                      fontWeight: '700',
                      textTransform: 'uppercase'
                    }}>
                      {rec.priority}
                    </span>
                  </div>
                  
                  {/* NLP Explanation */}
                  <div style={{ padding: '1rem' }}>
                    <div style={{ fontSize: '0.85rem', color: '#475569', lineHeight: '1.6', marginBottom: '0.75rem' }}>
                      {rec.message}
                    </div>
                    
                    {rec.details && (
                      <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '0.75rem', fontStyle: 'italic' }}>
                        {rec.details}
                      </div>
                    )}
                    
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '0.75rem',
                      background: '#f8fafc',
                      borderRadius: '6px'
                    }}>
                      <div>
                        <div style={{ fontSize: '0.7rem', color: '#64748b', marginBottom: '0.25rem' }}>RECOMMENDED ACTION</div>
                        <div style={{ fontSize: '0.85rem', fontWeight: '600', color: '#1e293b' }}>{rec.action}</div>
                      </div>
                      {rec.estimated_cost && (
                        <div style={{
                          padding: '0.5rem 0.75rem',
                          background: '#3d6b47',
                          color: '#fff',
                          borderRadius: '6px',
                          fontWeight: '600',
                          fontSize: '0.85rem'
                        }}>
                          {rec.estimated_cost}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* No Recommendations State */}
      {data.recommendations.length === 0 && (
        <div style={{
          padding: '2rem',
          textAlign: 'center',
          background: '#f0fdf4',
          borderRadius: '8px',
          border: '1px solid #bbf7d0',
          marginBottom: '1.5rem'
        }}>
          <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>✅</div>
          <div style={{ color: '#3d6b47', fontWeight: '600' }}>All systems healthy</div>
          <div style={{ color: '#64748b', fontSize: '0.85rem', marginTop: '0.25rem' }}>
            No immediate actions required. Continue monitoring inventory levels.
          </div>
        </div>
      )}

      {/* Financial Summary */}
      <div style={{ marginBottom: '1.5rem' }}>
        <h3 style={{ fontSize: '1rem', color: '#1e293b', marginBottom: '1rem', fontWeight: '600' }}>
          💰 Financial Summary
        </h3>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
          <tbody>
            <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={{ padding: '0.75rem 1rem', color: '#64748b', width: '40%' }}>Unit Cost</td>
              <td style={{ padding: '0.75rem 1rem', fontWeight: '600', color: '#1e293b' }}>${data.product.unit_cost.toFixed(2)}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={{ padding: '0.75rem 1rem', color: '#64748b' }}>Selling Price</td>
              <td style={{ padding: '0.75rem 1rem', fontWeight: '600', color: '#1e293b' }}>${data.product.unit_price.toFixed(2)}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={{ padding: '0.75rem 1rem', color: '#64748b' }}>Profit per Unit</td>
              <td style={{ padding: '0.75rem 1rem', fontWeight: '600', color: '#3d6b47' }}>${profitPerUnit.toFixed(2)}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={{ padding: '0.75rem 1rem', color: '#64748b' }}>Profit Margin</td>
              <td style={{ 
                padding: '0.75rem 1rem', 
                fontWeight: '600', 
                color: data.product.profit_margin > 40 ? '#3d6b47' : data.product.profit_margin > 20 ? '#8b6914' : '#b84444' 
              }}>
                {data.product.profit_margin}%
              </td>
            </tr>
            <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={{ padding: '0.75rem 1rem', color: '#64748b' }}>Total Stock Value</td>
              <td style={{ padding: '0.75rem 1rem', fontWeight: '600', color: '#1e293b' }}>
                ${(data.product.current_stock * data.product.unit_price).toLocaleString()}
              </td>
            </tr>
            <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={{ padding: '0.75rem 1rem', color: '#64748b' }}>Estimated Monthly Profit</td>
              <td style={{ padding: '0.75rem 1rem', fontWeight: '600', color: '#3d6b47' }}>${monthlyProfit.toFixed(2)}</td>
            </tr>
            <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={{ padding: '0.75rem 1rem', color: '#64748b' }}>Annual Holding Cost</td>
              <td style={{ padding: '0.75rem 1rem', fontWeight: '600', color: '#b84444' }}>${holdingCost.toFixed(2)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Slow Moving Product - Markdown Suggestion */}
      {isSlowMoving && (
        <div style={{
          background: '#fff',
          border: '1px solid #e2e8f0',
          borderRadius: '8px',
          padding: '1rem',
          marginBottom: '1.5rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
            <span style={{ fontSize: '1.25rem' }}>💡</span>
            <div>
              <div style={{ fontSize: '0.7rem', color: '#8b6914', marginBottom: '0.5rem', fontWeight: '600' }}>
                MARKDOWN OPPORTUNITY
              </div>
              <div style={{ fontSize: '0.85rem', color: '#334155', lineHeight: '1.6' }}>
                This product is moving at only <strong>{Math.round(data.metrics.average_daily_demand)} units/day</strong>. 
                A <strong>5% discount</strong> (new price: ${(data.product.unit_price * 0.95).toFixed(2)}) could accelerate sales. 
                Even at the reduced price, you'd recover <strong>${(data.product.current_stock * data.product.unit_price * 0.95).toLocaleString()}</strong> in 
                revenue versus the current slow movement which is costing you <strong>${holdingCost.toFixed(2)}/year</strong> just to store.
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ML Forecast Section */}
      {forecastData && !forecastData.error && (
        <div style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ fontSize: '1rem', color: '#1e293b', margin: 0, fontWeight: '600' }}>
              📈 Demand Forecast
            </h3>
            <button
              onClick={() => setShowForecast(!showForecast)}
              style={{
                padding: '0.4rem 0.75rem',
                background: '#f1f5f9',
                border: '1px solid #e2e8f0',
                borderRadius: '6px',
                color: '#4a6fa5',
                fontSize: '0.8rem',
                fontWeight: '600',
                cursor: 'pointer'
              }}
            >
              {showForecast ? '▲ Hide' : '▼ Show Details'}
            </button>
          </div>

          {/* Best Model Summary */}
          <div style={{
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            padding: '1rem',
            marginBottom: showForecast ? '1rem' : 0
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem' }}>
              <span style={{ fontSize: '1.25rem' }}>🏆</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '0.7rem', color: '#64748b', marginBottom: '0.25rem', fontWeight: '600' }}>
                  BEST PERFORMING MODEL
                </div>
                <div style={{ fontSize: '1rem', fontWeight: '600', color: '#1e293b', marginBottom: '0.5rem' }}>
                  {forecastData.best_model.name.replace(/_/g, ' ').toUpperCase()}
                </div>
                <div style={{ fontSize: '0.85rem', color: '#475569', lineHeight: '1.6' }}>
                  We ran multiple forecasting models and determined that{' '}
                  <strong>{forecastData.best_model.name.replace(/_/g, ' ')}</strong>{' '}
                  performs best for this product with <strong>{forecastData.best_model.accuracy}% accuracy</strong>.{' '}
                  {forecastData.recommendation}
                </div>
              </div>
            </div>
          </div>

          {showForecast && (
            <>
              {/* Models Performance */}
              <h4 style={{ fontSize: '0.9rem', color: '#1e293b', marginBottom: '0.75rem', fontWeight: '600' }}>
                Model Comparison
              </h4>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', marginBottom: '1rem' }}>
                <thead>
                  <tr style={{ background: '#f8fafc' }}>
                    <th style={{ padding: '0.6rem 0.75rem', textAlign: 'left', borderBottom: '2px solid #e2e8f0', color: '#64748b', fontWeight: '600' }}>Model</th>
                    <th style={{ padding: '0.6rem 0.75rem', textAlign: 'center', borderBottom: '2px solid #e2e8f0', color: '#64748b', fontWeight: '600' }}>Accuracy</th>
                    <th style={{ padding: '0.6rem 0.75rem', textAlign: 'center', borderBottom: '2px solid #e2e8f0', color: '#64748b', fontWeight: '600' }}>Forecast</th>
                    <th style={{ padding: '0.6rem 0.75rem', textAlign: 'center', borderBottom: '2px solid #e2e8f0', color: '#64748b', fontWeight: '600' }}>Trend</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(forecastData.models_performance).map(([modelName, perf], idx) => (
                    <tr key={idx} style={{ 
                      background: modelName === forecastData.best_model.name ? '#f0fdf4' : 'transparent',
                      borderBottom: '1px solid #e2e8f0'
                    }}>
                      <td style={{ padding: '0.6rem 0.75rem' }}>
                        {modelName.replace(/_/g, ' ')}
                        {modelName === forecastData.best_model.name && (
                          <span style={{ marginLeft: '0.5rem', fontSize: '0.65rem', background: '#3d6b47', color: '#fff', padding: '0.15rem 0.35rem', borderRadius: '3px' }}>BEST</span>
                        )}
                      </td>
                      <td style={{ 
                        padding: '0.6rem 0.75rem', 
                        textAlign: 'center',
                        fontWeight: '600',
                        color: perf.accuracy > 85 ? '#3d6b47' : perf.accuracy > 70 ? '#8b6914' : '#b84444'
                      }}>
                        {perf.accuracy}%
                      </td>
                      <td style={{ padding: '0.6rem 0.75rem', textAlign: 'center', fontWeight: '600' }}>
                        {perf.last_forecast.toFixed(1)} units
                      </td>
                      <td style={{ padding: '0.6rem 0.75rem', textAlign: 'center' }}>
                        {perf.trend === 'increasing' && <span style={{ color: '#3d6b47' }}>📈 Up</span>}
                        {perf.trend === 'decreasing' && <span style={{ color: '#b84444' }}>📉 Down</span>}
                        {perf.trend === 'stable' && <span style={{ color: '#64748b' }}>➡️ Stable</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* 7-Day Forecast */}
              <h4 style={{ fontSize: '0.9rem', color: '#1e293b', marginBottom: '0.75rem', fontWeight: '600' }}>
                Next 7 Days Forecast
              </h4>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                <thead>
                  <tr style={{ background: '#f8fafc' }}>
                    <th style={{ padding: '0.6rem 0.75rem', textAlign: 'left', borderBottom: '2px solid #e2e8f0', color: '#64748b', fontWeight: '600' }}>Date</th>
                    <th style={{ padding: '0.6rem 0.75rem', textAlign: 'center', borderBottom: '2px solid #e2e8f0', color: '#64748b', fontWeight: '600' }}>Best Model</th>
                    <th style={{ padding: '0.6rem 0.75rem', textAlign: 'center', borderBottom: '2px solid #e2e8f0', color: '#64748b', fontWeight: '600' }}>Ensemble</th>
                  </tr>
                </thead>
                <tbody>
                  {forecastData.forecast.dates.slice(0, 7).map((date, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid #e2e8f0' }}>
                      <td style={{ padding: '0.6rem 0.75rem' }}>
                        {new Date(date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                      </td>
                      <td style={{ padding: '0.6rem 0.75rem', textAlign: 'center', fontWeight: '600', color: '#4a6fa5' }}>
                        {forecastData.forecast.best_model[idx].toFixed(1)} units
                      </td>
                      <td style={{ padding: '0.6rem 0.75rem', textAlign: 'center', fontWeight: '600', color: '#3d6b47' }}>
                        {forecastData.forecast.ensemble[idx].toFixed(1)} units
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default ProductInsightModal;
