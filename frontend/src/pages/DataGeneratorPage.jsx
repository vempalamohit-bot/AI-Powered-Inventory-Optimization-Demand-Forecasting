import { useState } from 'react';
import '../styles/DataGenerator.css';
import SampleDataCard from '../components/SampleDataCard';
import { dataService } from '../services/api';

export default function DataGeneratorPage() {
  const [isLoading, setIsLoading] = useState(false);
  const [generatedData, setGeneratedData] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);
  const [successMessage, setSuccessMessage] = useState('');
  const [days, setDays] = useState(90);

  const handleGenerateData = async () => {
    setIsLoading(true);
    setError(null);
    setSuccessMessage('');
    
    try {
      const response = await dataService.generateSampleData(days);
      const data = response.data;
      
      if (data.status === 'success') {
        setGeneratedData(data.data_sample);
        setSummary(data.summary);
        setSuccessMessage(`✅ Successfully generated ${data.records_created} sample records!`);
      } else {
        setError(data.message || 'Failed to generate data');
      }
    } catch (err) {
      setError(err.message || 'Error generating data');
      console.error('Data generation error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="data-generator-container">
      <div className="generator-header">
        <h1>📊 Smart Sample Data Generator</h1>
        <p>Generate realistic sales data with seasonal patterns, holidays, and external signals</p>
      </div>

      <div className="generator-controls">
        <div className="control-group">
          <label htmlFor="days-input">Days of History:</label>
          <input
            id="days-input"
            type="number"
            min="7"
            max="365"
            value={days}
            onChange={(e) => setDays(parseInt(e.target.value))}
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
          className="btn-generate"
          onClick={handleGenerateData}
          disabled={isLoading}
        >
          {isLoading ? '⏳ Generating...' : '🚀 Generate Sample Data'}
        </button>
      </div>

      {error && (
        <div className="alert alert-error">
          <span className="alert-icon">❌</span>
          <span>{error}</span>
        </div>
      )}

      {successMessage && (
        <div className="alert alert-success">
          <span className="alert-icon">✅</span>
          <span>{successMessage}</span>
        </div>
      )}

      {summary && (
        <div className="summary-section">
          <div className="summary-grid">
            <div className="summary-card">
              <div className="summary-label">Total Records</div>
              <div className="summary-value">{summary.total_records}</div>
            </div>
            <div className="summary-card">
              <div className="summary-label">Products</div>
              <div className="summary-value">{summary.products_count}</div>
            </div>
            <div className="summary-card">
              <div className="summary-label">Total Revenue</div>
              <div className="summary-value">${summary.total_revenue?.toLocaleString() || 0}</div>
            </div>
            <div className="summary-card">
              <div className="summary-label">Units Sold</div>
              <div className="summary-value">{summary.total_units_sold?.toLocaleString() || 0}</div>
            </div>
          </div>

          <div className="products-list">
            <h3>Products Generated:</h3>
            <ul>
              {summary.products?.map((product) => (
                <li key={product}>
                  <span className="product-badge">{product.replace('_', ' ')}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {generatedData && (
        <div className="data-preview-section">
          <h3>📈 Sample Data (First 10 Records)</h3>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>SKU</th>
                  <th>Product</th>
                  <th>Category</th>
                  <th>Qty Sold</th>
                  <th>Revenue</th>
                  <th>Factors</th>
                </tr>
              </thead>
              <tbody>
                {generatedData.map((row, idx) => (
                  <tr key={idx}>
                    <td>{row.date}</td>
                    <td><code>{row.sku}</code></td>
                    <td>{row.product_name}</td>
                    <td>{row.category}</td>
                    <td className="qty-cell">{row.quantity_sold}</td>
                    <td className="revenue-cell">${row.revenue?.toFixed(2) || 0}</td>
                    <td className="factors-cell">
                      <details>
                        <summary>View</summary>
                        <div className="factors-detail">
                          {Object.entries(row.factors || {}).map(([key, val]) => (
                            <div key={key}>
                              <strong>{key}:</strong> {val}x
                            </div>
                          ))}
                        </div>
                      </details>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {generatedData && (
        <div className="insights-section">
          <h3>💡 How This Data Works</h3>
          <div className="insights-grid">
            <SampleDataCard
              title="🌞 Seasonal Patterns"
              description="Products peak in their preferred seasons: Ice cream in summer (2x), winter coats in winter (2.5x)"
              icon="📊"
            />
            <SampleDataCard
              title="🎉 Holiday Boosts"
              description="Valentine's Day gets 1.5x boost, Christmas gets 3.0x boost for relevant products"
              icon="🎄"
            />
            <SampleDataCard
              title="💰 Payday Effect"
              description="Purchasing increases on payday (15th & 30th) by 1.3x due to salary deposits"
              icon="💳"
            />
            <SampleDataCard
              title="📱 Viral Trends"
              description="5% chance of random 3x spikes (trending products, celebrity mentions, viral posts)"
              icon="🚀"
            />
            <SampleDataCard
              title="🛍️ Weekend Traffic"
              description="Weekend sales are 1.5x higher than weekdays due to retail foot traffic"
              icon="🏪"
            />
            <SampleDataCard
              title="🌦️ Weather Impact"
              description="External weather signals (temperature, conditions) affect product demand"
              icon="⛅"
            />
          </div>
        </div>
      )}
    </div>
  );
}
