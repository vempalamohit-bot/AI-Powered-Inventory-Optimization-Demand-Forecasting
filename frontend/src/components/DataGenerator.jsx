import React, { useState, useEffect } from 'react';
import { apiClient } from '../services/api';
import './DataGenerator.css';

export default function DataGenerator() {
  const [isLoading, setIsLoading] = useState(false);
  const [summary, setSummary] = useState(null);
  const [signals, setSignals] = useState(null);
  const [selectedDate, setSelectedDate] = useState(
    new Date().toISOString().split('T')[0]
  );
  const [selectedProduct, setSelectedProduct] = useState('');

  // Generate sample data
  const handleGenerateData = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.post('/generate-sample-data', {});
      setSummary(response.data.summary);
      alert('✅ Sample data generated successfully!');
    } catch (error) {
      alert(`❌ Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Get data summary
  const handleGetSummary = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get('/data-generator/summary');
      if (response.data.status === 'no_data') {
        alert('No data available. Generate sample data first.');
      } else {
        setSummary(response.data.summary);
      }
    } catch (error) {
      alert(`❌ Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // Get combined signals
  const handleGetSignals = async () => {
    setIsLoading(true);
    try {
      const response = await apiClient.get(
        `/signals/combined/${selectedDate}?product=${selectedProduct}`
      );
      setSignals(response.data.signals);
    } catch (error) {
      alert(`❌ Error: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="data-generator-container">
      <div className="generator-header">
        <h1>📊 Smart Data Generator</h1>
        <p>Generate realistic sample data + HyperLocal Signals</p>
      </div>

      <div className="generator-grid">
        {/* Section 1: Data Generation */}
        <div className="generator-card">
          <div className="card-header">
            <h2>🎲 Generate Sample Data</h2>
            <p>90 days of realistic seasonal sales patterns</p>
          </div>
          
          <div className="card-content">
            <div className="info-box">
              <h4>What this does:</h4>
              <ul>
                <li>✓ 5 realistic products (ice cream, coats, drinks, etc.)</li>
                <li>✓ 90 days of daily sales history</li>
                <li>✓ Seasonal patterns (summer/winter spikes)</li>
                <li>✓ Weekend boosts (1.5x multiplier)</li>
                <li>✓ Holiday impacts (1.3x to 3.0x)</li>
                <li>✓ Payday effects (15th, 30th +30%)</li>
                <li>✓ Viral/trend spikes (random 3x events)</li>
                <li>✓ Weather correlations</li>
              </ul>
            </div>

            <button
              onClick={handleGenerateData}
              disabled={isLoading}
              className="btn btn-primary"
            >
              {isLoading ? '⏳ Generating...' : '🚀 Generate 90 Days Data'}
            </button>

            <button
              onClick={handleGetSummary}
              disabled={isLoading}
              className="btn btn-secondary"
            >
              📈 View Summary
            </button>
          </div>

          {summary && (
            <div className="summary-display">
              <h3>📊 Data Summary</h3>
              <div className="summary-grid">
                <div className="metric">
                  <label>Total Records</label>
                  <value>{summary.total_records}</value>
                </div>
                <div className="metric">
                  <label>Date Range</label>
                  <value>
                    {summary.date_range.start} to {summary.date_range.end}
                  </value>
                </div>
                <div className="metric">
                  <label>Products</label>
                  <value>{summary.products_count}</value>
                </div>
                <div className="metric">
                  <label>Total Revenue</label>
                  <value>${summary.total_revenue.toLocaleString()}</value>
                </div>
                <div className="metric">
                  <label>Total Units Sold</label>
                  <value>{summary.total_units_sold.toLocaleString()}</value>
                </div>
                <div className="metric">
                  <label>Avg Daily Revenue</label>
                  <value>${summary.avg_daily_revenue.toLocaleString()}</value>
                </div>
              </div>

              <div className="breakdown">
                <h4>By Category</h4>
                <div className="breakdown-items">
                  {Object.entries(summary.by_category).map(([category, revenue]) => (
                    <div key={category} className="breakdown-item">
                      <span>{category}</span>
                      <strong>${revenue.toLocaleString()}</strong>
                    </div>
                  ))}
                </div>
              </div>

              <div className="breakdown">
                <h4>By Product</h4>
                <div className="breakdown-items">
                  {summary.products.map((product) => (
                    <div key={product} className="breakdown-item">
                      <span>{product}</span>
                      <strong>
                        {
                          summary.by_product[product][0] ||
                          summary.by_product[product].quantity_sold
                        }{' '}
                        units
                      </strong>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Section 2: HyperLocal Signals */}
        <div className="generator-card">
          <div className="card-header">
            <h2>🌐 HyperLocal Signals</h2>
            <p>External factors influencing demand</p>
          </div>

          <div className="card-content">
            <div className="input-group">
              <label>Select Date</label>
              <input
                type="date"
                value={selectedDate}
                onChange={(e) => setSelectedDate(e.target.value)}
                style={{
                  padding: '0.6rem',
                  fontSize: '1rem',
                  border: '2px solid #ddd',
                  borderRadius: '4px',
                  backgroundColor: '#ffffff',
                  color: '#000000',
                  fontWeight: '600',
                  width: '100%'
                }}
              />
            </div>

            <div className="input-group">
              <label>Product (Optional)</label>
              <input
                type="text"
                placeholder="e.g., ICE_CREAM"
                value={selectedProduct}
                onChange={(e) => setSelectedProduct(e.target.value)}
                style={{
                  padding: '0.6rem',
                  fontSize: '1rem',
                  border: '2px solid #ddd',
                  borderRadius: '4px',
                  backgroundColor: '#ffffff',
                  color: '#000000',
                  fontWeight: '600',
                  width: '100%'
                }}
              />
            </div>

            <button
              onClick={handleGetSignals}
              disabled={isLoading}
              className="btn btn-primary"
            >
              {isLoading ? '⏳ Fetching...' : '🔍 Analyze Signals'}
            </button>

            <div className="signal-info">
              <h4>Signal Types:</h4>
              <ul>
                <li>🌡️ <strong>Weather</strong> - Seasonal impact</li>
                <li>🎉 <strong>Holidays</strong> - Special events</li>
                <li>💰 <strong>Payday</strong> - 15th & 30th boost</li>
                <li>📅 <strong>Weekend</strong> - Sat/Sun traffic</li>
                <li>📱 <strong>Trends</strong> - Viral moments</li>
              </ul>
            </div>
          </div>

          {signals && (
            <div className="signals-display">
              <h3>📡 Combined Signals for {selectedDate}</h3>

              <div className="signal-multiplier">
                <div className="multiplier-badge">
                  <span>Combined Multiplier</span>
                  <strong className="multiplier-value">
                    {signals.combined_multiplier}x
                  </strong>
                </div>
                <p className="multiplier-info">
                  {signals.interpretation}
                </p>
              </div>

              <div className="signals-grid">
                {/* Weather */}
                {signals.weather && (
                  <div className="signal-card">
                    <h4>🌡️ Weather</h4>
                    <div className="signal-content">
                      <p>
                        <strong>Season:</strong> {signals.weather.season}
                      </p>
                      <p>
                        <strong>Temperature:</strong> {signals.weather.temp_range}
                      </p>
                      <p>
                        <strong>Condition:</strong> {signals.weather.condition}
                      </p>
                      <p>
                        <strong>Boost:</strong> {signals.weather.boost_factor}x
                      </p>
                      <p className="impact">{signals.weather.impact}</p>
                      {signals.weather.affected_products.length > 0 && (
                        <p className="products">
                          Affects: {signals.weather.affected_products.join(', ')}
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* Holiday */}
                {signals.holiday && (
                  <div className="signal-card">
                    <h4>🎉 Holiday</h4>
                    <div className="signal-content">
                      <p>
                        <strong>Holiday:</strong> {signals.holiday.holiday}
                      </p>
                      <p>
                        <strong>Boost:</strong> {signals.holiday.boost}x
                      </p>
                      <p className="impact">{signals.holiday.description}</p>
                      {signals.holiday.affected_products.length > 0 && (
                        <p className="products">
                          Affects: {signals.holiday.affected_products.join(', ')}
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* Payday */}
                {signals.payday && (
                  <div className="signal-card">
                    <h4>💰 Payday</h4>
                    <div className="signal-content">
                      <p>
                        <strong>Status:</strong>{' '}
                        {signals.payday.is_payday ? 'YES ✓' : 'No'}
                      </p>
                      {signals.payday.payday_date && (
                        <p>
                          <strong>Date:</strong> {signals.payday.payday_date}th of
                          month
                        </p>
                      )}
                      <p>
                        <strong>Boost:</strong> {signals.payday.boost}x
                      </p>
                      <p className="impact">{signals.payday.description}</p>
                    </div>
                  </div>
                )}

                {/* Weekend */}
                {signals.weekend && (
                  <div className="signal-card">
                    <h4>📅 Weekend</h4>
                    <div className="signal-content">
                      <p>
                        <strong>Day:</strong> {signals.weekend.day}
                      </p>
                      <p>
                        <strong>Is Weekend:</strong>{' '}
                        {signals.weekend.is_weekend ? 'YES ✓' : 'No'}
                      </p>
                      <p>
                        <strong>Boost:</strong> {signals.weekend.boost}x
                      </p>
                      <p className="impact">{signals.weekend.description}</p>
                    </div>
                  </div>
                )}

                {/* Trends */}
                {signals.trend && (
                  <div className="signal-card">
                    <h4>📱 Trends</h4>
                    <div className="signal-content">
                      <p>
                        <strong>Trending:</strong>{' '}
                        {signals.trend.is_trending ? 'YES ✓' : 'No'}
                      </p>
                      {signals.trend.is_trending && (
                        <>
                          <p>
                            <strong>Trend:</strong> {signals.trend.trend}
                          </p>
                          <p>
                            <strong>Product:</strong> {signals.trend.product}
                          </p>
                          <p>
                            <strong>Boost:</strong> {signals.trend.boost}x
                          </p>
                          <p>
                            <strong>Duration:</strong>{' '}
                            {signals.trend.duration_days} days
                          </p>
                        </>
                      )}
                      <p className="impact">{signals.trend.description}</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
