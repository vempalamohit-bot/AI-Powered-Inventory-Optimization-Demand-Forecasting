import { useState } from 'react';
import '../styles/SignalsEnrichment.css';

export default function SignalsEnrichmentComponent() {
  const [selectedProduct, setSelectedProduct] = useState('ICE_CREAM');
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [signals, setSignals] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const products = [
    { id: 1, sku: 'ICE_CREAM', name: 'Premium Ice Cream' },
    { id: 2, sku: 'WINTER_COAT', name: 'Winter Coat' },
    { id: 3, sku: 'ENERGY_DRINK', name: 'Energy Drink' },
    { id: 4, sku: 'HOT_COCOA', name: 'Hot Cocoa' },
    { id: 5, sku: 'SUNSCREEN', name: 'Sunscreen SPF 50' }
  ];

  const handleEnrichForecast = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const product = products.find(p => p.sku === selectedProduct);
      const response = await fetch(
        `http://localhost:8000/api/data/enrich-forecast/${product.id}?date=${selectedDate}`
      );
      const data = await response.json();
      
      if (data.status === 'success') {
        setForecast(data.forecast);
        setSignals(data.signals_breakdown);
      } else {
        setError(data.message || 'Failed to enrich forecast');
      }
    } catch (err) {
      setError(err.message || 'Error enriching forecast');
    } finally {
      setIsLoading(false);
    }
  };

  const getSignalColor = (value) => {
    if (value >= 2.0) return '#ff6b6b'; // Red for high boost
    if (value >= 1.5) return '#ffa500'; // Orange for medium boost
    if (value > 1.0) return '#4ecdc4'; // Teal for slight boost
    if (value === 1.0) return '#95e1d3'; // Light teal for neutral
    return '#ffe66d'; // Yellow for reduction
  };

  return (
    <div className="signals-container">
      <div className="signals-header">
        <h2>🎯 Hyper-Local Signals Enrichment</h2>
        <p>Enhance forecasts with weather, holidays, paydays, and weekend signals</p>
      </div>

      <div className="signals-controls">
        <div className="control-group">
          <label htmlFor="product-select">Product:</label>
          <select
            id="product-select"
            value={selectedProduct}
            onChange={(e) => setSelectedProduct(e.target.value)}
            disabled={isLoading}
            style={{
              padding: '0.6rem',
              fontSize: '1rem',
              border: '2px solid #ddd',
              borderRadius: '4px',
              backgroundColor: '#ffffff',
              color: '#000000',
              fontWeight: '600'
            }}
          >
            {products.map(p => (
              <option key={p.sku} value={p.sku}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <div className="control-group">
          <label htmlFor="date-input">Date:</label>
          <input
            id="date-input"
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            disabled={isLoading}
            style={{
              padding: '0.6rem',
              fontSize: '1rem',
              border: '2px solid #ddd',
              borderRadius: '4px',
              backgroundColor: '#ffffff',
              color: '#000000',
              fontWeight: '600'
            }}
          />
        </div>

        <button
          className="btn-enrich"
          onClick={handleEnrichForecast}
          disabled={isLoading}
        >
          {isLoading ? '⏳ Enriching...' : '✨ Enrich Forecast'}
        </button>
      </div>

      {error && (
        <div className="alert alert-error">
          <span>❌ {error}</span>
        </div>
      )}

      {forecast && signals && (
        <div className="signals-results">
          {/* Forecast Summary */}
          <div className="forecast-summary">
            <h3>📈 Forecast Summary</h3>
            <div className="forecast-grid">
              <div className="forecast-item">
                <span className="label">Base Forecast</span>
                <span className="value">{Math.round(forecast.base_forecast)} units</span>
              </div>
              <div className="forecast-item">
                <span className="label">Signal Multiplier</span>
                <span className="value" style={{ color: getSignalColor(forecast.signal_multiplier) }}>
                  {forecast.signal_multiplier}x
                </span>
              </div>
              <div className="forecast-item">
                <span className="label">Enriched Forecast</span>
                <span className="value highlight">{forecast.enriched_forecast} units</span>
              </div>
              <div className="forecast-item">
                <span className="label">Confidence</span>
                <span className="value">{(forecast.confidence * 100).toFixed(0)}%</span>
              </div>
            </div>
            <div className="insight-text">
              <strong>💡 Insight:</strong> {forecast.signal_multiplier > 1.2 
                ? `📈 High demand expected (${forecast.signal_multiplier}x multiplier)`
                : forecast.signal_multiplier < 0.8
                ? `📉 Low demand expected (${forecast.signal_multiplier}x multiplier)`
                : `➡️ Normal demand expected (${forecast.signal_multiplier}x multiplier)`}
            </div>
          </div>

          {/* Signals Breakdown */}
          <div className="signals-breakdown">
            <h3>🔍 Signal Breakdown</h3>

            {/* Weather Signal */}
            <div className="signal-card weather-signal">
              <div className="signal-header">
                <span className="signal-emoji">🌡️</span>
                <h4>Weather Signal</h4>
                <span className="signal-boost" style={{ color: getSignalColor(signals.weather.boost_factor) }}>
                  {signals.weather.boost_factor}x
                </span>
              </div>
              <div className="signal-content">
                <p><strong>Season:</strong> {signals.weather.season}</p>
                <p><strong>Condition:</strong> {signals.weather.condition}</p>
                <p><strong>Impact:</strong> {signals.weather.impact}</p>
                <div className="affected-products">
                  {signals.weather.affected_products.map((prod, idx) => (
                    <span key={idx} className="product-tag">{prod}</span>
                  ))}
                </div>
              </div>
            </div>

            {/* Holiday Signal */}
            <div className="signal-card holiday-signal">
              <div className="signal-header">
                <span className="signal-emoji">🎉</span>
                <h4>Holiday Signal</h4>
                <span className="signal-boost" style={{ color: getSignalColor(signals.holiday.boost) }}>
                  {signals.holiday.boost}x
                </span>
              </div>
              <div className="signal-content">
                <p><strong>Holiday:</strong> {signals.holiday.holiday}</p>
                <p><strong>Description:</strong> {signals.holiday.description}</p>
                <div className="affected-products">
                  {signals.holiday.affected_products.map((prod, idx) => (
                    <span key={idx} className="product-tag">{prod}</span>
                  ))}
                </div>
              </div>
            </div>

            {/* Payday Signal */}
            <div className="signal-card payday-signal">
              <div className="signal-header">
                <span className="signal-emoji">💰</span>
                <h4>Payday Signal</h4>
                <span className="signal-boost" style={{ color: getSignalColor(signals.payday.boost) }}>
                  {signals.payday.boost}x
                </span>
              </div>
              <div className="signal-content">
                <p><strong>Status:</strong> {signals.payday.is_payday ? '✅ Payday' : '❌ Regular Day'}</p>
                <p><strong>Date:</strong> {signals.payday.payday_date ? `${signals.payday.payday_date}th` : 'N/A'}</p>
                <p><strong>Description:</strong> {signals.payday.description}</p>
              </div>
            </div>

            {/* Weekend Signal */}
            <div className="signal-card weekend-signal">
              <div className="signal-header">
                <span className="signal-emoji">📅</span>
                <h4>Weekend Signal</h4>
                <span className="signal-boost" style={{ color: getSignalColor(signals.weekend.boost) }}>
                  {signals.weekend.boost}x
                </span>
              </div>
              <div className="signal-content">
                <p><strong>Day:</strong> {signals.weekend.day}</p>
                <p><strong>Is Weekend:</strong> {signals.weekend.is_weekend ? '✅ Yes' : '❌ No'}</p>
                <p><strong>Description:</strong> {signals.weekend.description}</p>
              </div>
            </div>

            {/* Trend Signal */}
            {signals.trend.is_trending && (
              <div className="signal-card trend-signal trending">
                <div className="signal-header">
                  <span className="signal-emoji">🚀</span>
                  <h4>Viral Trend Alert</h4>
                  <span className="signal-boost trending-boost" style={{ color: getSignalColor(signals.trend.boost) }}>
                    {signals.trend.boost}x
                  </span>
                </div>
                <div className="signal-content">
                  <p><strong>Trend:</strong> {signals.trend.trend}</p>
                  <p><strong>Product:</strong> {signals.trend.product}</p>
                  <p><strong>Description:</strong> {signals.trend.description}</p>
                  <p><strong>Duration:</strong> ~{signals.trend.duration_days} days</p>
                  <p><strong>Confidence:</strong> {(signals.trend.confidence * 100).toFixed(0)}%</p>
                </div>
              </div>
            )}
          </div>

          {/* Combined Interpretation */}
          <div className="combined-interpretation">
            <h3>📊 Combined Forecast Adjustment</h3>
            <p className="interpretation-text">{forecast.interpretation || 'Loading...'}</p>
            <div className="adjustment-breakdown">
              <p>✅ Weather: {signals.weather.boost_factor}x</p>
              <p>✅ Holiday: {signals.holiday.boost}x</p>
              <p>✅ Payday: {signals.payday.boost}x</p>
              <p>✅ Weekend: {signals.weekend.boost}x</p>
              {signals.trend.is_trending && <p>✅ Trend: {signals.trend.boost}x</p>}
              <p className="total">= {forecast.signal_multiplier}x combined multiplier</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
