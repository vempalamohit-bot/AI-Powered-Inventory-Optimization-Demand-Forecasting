import React, { useState, useEffect } from 'react';
import apiClient from '../services/api';

const ApiIntegration = () => {
    const [templates, setTemplates] = useState([]);
    const [loading, setLoading] = useState(false);
    const [importResult, setImportResult] = useState(null);
    const [customUrl, setCustomUrl] = useState('');
    const [dataType, setDataType] = useState('products');
    const [previewData, setPreviewData] = useState(null);
    const [previewLoading, setPreviewLoading] = useState(false);
    const [generateConfig, setGenerateConfig] = useState({
        count: 100,
        includeExtraColumns: true,
        extraColumns: ['supplier', 'warehouse_location', 'min_order_qty', 'max_stock_level', 'brand', 'weight_kg']
    });

    useEffect(() => {
        loadTemplates();
    }, []);

    const loadTemplates = async () => {
        try {
            const response = await apiClient.get('/data/external-api-templates');
            setTemplates(response.data.templates || []);
        } catch (error) {
            console.error('Failed to load API templates:', error);
        }
    };

    const previewApi = async (url) => {
        setPreviewLoading(true);
        setPreviewData(null);
        try {
            const response = await fetch(url);
            const data = await response.json();
            // Get first 5 items for preview
            let items = data;
            if (data.products) items = data.products;
            else if (data.data) items = data.data;
            else if (data.items) items = data.items;
            
            setPreviewData(Array.isArray(items) ? items.slice(0, 5) : [items]);
        } catch (error) {
            console.error('Preview failed:', error);
            setPreviewData([{ error: 'Failed to fetch preview' }]);
        }
        setPreviewLoading(false);
    };

    const importFromApi = async (url, type = 'products') => {
        setLoading(true);
        setImportResult(null);
        try {
            const response = await apiClient.post(`/data/import-from-api?api_url=${encodeURIComponent(url)}&data_type=${type}`);
            setImportResult({
                success: true,
                ...response.data
            });
        } catch (error) {
            setImportResult({
                success: false,
                message: error.response?.data?.detail || 'Import failed'
            });
        }
        setLoading(false);
    };

    const generateSampleData = async () => {
        setLoading(true);
        setImportResult(null);
        try {
            const response = await apiClient.post('/data/generate-from-dummyjson', generateConfig);
            setImportResult({
                success: true,
                ...response.data
            });
        } catch (error) {
            setImportResult({
                success: false,
                message: error.response?.data?.detail || 'Generation failed'
            });
        }
        setLoading(false);
    };

    const toggleExtraColumn = (col) => {
        setGenerateConfig(prev => ({
            ...prev,
            extraColumns: prev.extraColumns.includes(col)
                ? prev.extraColumns.filter(c => c !== col)
                : [...prev.extraColumns, col]
        }));
    };

    return (
        <div className="page-container">
            <div className="container">
                {/* Page Header */}
                <div className="page-header">
                    <h1 className="page-title">API Integration</h1>
                    <p className="page-subtitle">
                        Import data from free external APIs or generate sample data with custom columns
                    </p>
                </div>

                {/* Powered by Open Source Banner */}
                <div style={{
                    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    borderRadius: '12px',
                    padding: '1rem 1.5rem',
                    marginBottom: 'var(--spacing-4)',
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '1rem'
                }}>
                    <span style={{ fontSize: '2rem' }}>🔓</span>
                    <div>
                        <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>Powered by Open-Source Analytics</div>
                        <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>
                            All forecasting uses free libraries: statsmodels (ARIMA, Holt-Winters), scikit-learn, scipy, pandas. No paid APIs required.
                        </div>
                    </div>
                </div>

                {/* External API Data Generator Section */}
                <div className="card" style={{ marginBottom: 'var(--spacing-4)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: 'var(--spacing-3)' }}>
                        <span style={{ fontSize: '1.5rem' }}>🎲</span>
                        <div>
                            <h3 style={{ margin: 0 }}>Generate Sample Data from External API</h3>
                            <p style={{ margin: '0.25rem 0 0 0', color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                                Fetch real product data from external API with additional custom columns for your inventory
                            </p>
                        </div>
                    </div>

                    <div style={{ 
                        background: 'var(--bg-secondary)', 
                        borderRadius: '8px', 
                        padding: '1rem',
                        marginBottom: 'var(--spacing-3)'
                    }}>
                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ fontWeight: 600, display: 'block', marginBottom: '0.5rem' }}>
                                Number of Products to Generate
                            </label>
                            <input
                                type="number"
                                value={generateConfig.count}
                                onChange={(e) => setGenerateConfig(prev => ({ ...prev, count: parseInt(e.target.value) || 100 }))}
                                min="10"
                                max="1000"
                                style={{
                                    padding: '0.5rem 0.75rem',
                                    border: '1px solid var(--border-color)',
                                    borderRadius: '6px',
                                    width: '150px'
                                }}
                            />
                        </div>

                        <div style={{ marginBottom: '1rem' }}>
                            <label style={{ fontWeight: 600, display: 'block', marginBottom: '0.5rem' }}>
                                <input
                                    type="checkbox"
                                    checked={generateConfig.includeExtraColumns}
                                    onChange={(e) => setGenerateConfig(prev => ({ ...prev, includeExtraColumns: e.target.checked }))}
                                    style={{ marginRight: '0.5rem' }}
                                />
                                Include Extra Columns (Beyond Standard Fields)
                            </label>
                        </div>

                        {generateConfig.includeExtraColumns && (
                            <div>
                                <label style={{ fontWeight: 600, display: 'block', marginBottom: '0.75rem' }}>
                                    Select Extra Columns to Generate:
                                </label>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                                    {['supplier', 'warehouse_location', 'min_order_qty', 'max_stock_level', 'brand', 'weight_kg', 'dimensions', 'barcode', 'manufacturer', 'country_of_origin'].map(col => (
                                        <button
                                            key={col}
                                            onClick={() => toggleExtraColumn(col)}
                                            style={{
                                                padding: '0.4rem 0.75rem',
                                                borderRadius: '20px',
                                                border: 'none',
                                                cursor: 'pointer',
                                                fontSize: '0.85rem',
                                                background: generateConfig.extraColumns.includes(col) ? '#3b82f6' : '#e5e7eb',
                                                color: generateConfig.extraColumns.includes(col) ? 'white' : '#374151',
                                                transition: 'all 0.2s'
                                            }}
                                        >
                                            {generateConfig.extraColumns.includes(col) ? '✓ ' : ''}{col.replace(/_/g, ' ')}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    <button
                        onClick={generateSampleData}
                        disabled={loading}
                        className="btn btn-primary"
                        style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
                    >
                        {loading ? (
                            <>
                                <svg className="spinner" width="16" height="16" viewBox="0 0 24 24">
                                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none"/>
                                </svg>
                                Generating...
                            </>
                        ) : (
                            <>🚀 Generate &amp; Import Data</>
                        )}
                    </button>
                </div>

                {/* Pre-configured API Templates */}
                <div className="card" style={{ marginBottom: 'var(--spacing-4)' }}>
                    <h3 className="mb-2">Free API Templates</h3>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--spacing-3)', fontSize: '0.9rem' }}>
                        Click any template to preview data, then import directly to your inventory database.
                    </p>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
                        {templates.map((template, idx) => (
                            <div 
                                key={idx}
                                style={{
                                    border: '1px solid var(--border-color)',
                                    borderRadius: '8px',
                                    padding: '1rem',
                                    background: 'var(--bg-secondary)'
                                }}
                            >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                                    <span style={{ fontSize: '1.25rem' }}>{template.icon}</span>
                                    <strong>{template.name}</strong>
                                </div>
                                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                                    {template.description}
                                </p>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                                    Fields: {template.fields_mapped?.join(', ')}
                                </div>
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                    <button
                                        onClick={() => previewApi(template.url)}
                                        className="btn btn-secondary"
                                        style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
                                        disabled={previewLoading}
                                    >
                                        👁️ Preview
                                    </button>
                                    <button
                                        onClick={() => importFromApi(template.url, template.data_type)}
                                        className="btn btn-primary"
                                        style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem' }}
                                        disabled={loading}
                                    >
                                        📥 Import
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Custom API URL */}
                <div className="card" style={{ marginBottom: 'var(--spacing-4)' }}>
                    <h3 className="mb-2">Custom API URL</h3>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: 'var(--spacing-3)', fontSize: '0.9rem' }}>
                        Enter any JSON API URL that returns an array of objects. The system will auto-map common field names.
                    </p>
                    
                    <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
                        <input
                            type="text"
                            value={customUrl}
                            onChange={(e) => setCustomUrl(e.target.value)}
                            placeholder="https://api.example.com/products"
                            style={{
                                flex: 1,
                                padding: '0.5rem 0.75rem',
                                border: '1px solid var(--border-color)',
                                borderRadius: '6px'
                            }}
                        />
                        <select
                            value={dataType}
                            onChange={(e) => setDataType(e.target.value)}
                            style={{
                                padding: '0.5rem 0.75rem',
                                border: '1px solid var(--border-color)',
                                borderRadius: '6px'
                            }}
                        >
                            <option value="products">Products</option>
                            <option value="sales">Sales History</option>
                            <option value="inventory">Stock Update</option>
                        </select>
                    </div>
                    
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                            onClick={() => previewApi(customUrl)}
                            className="btn btn-secondary"
                            disabled={!customUrl || previewLoading}
                        >
                            👁️ Preview Data
                        </button>
                        <button
                            onClick={() => importFromApi(customUrl, dataType)}
                            className="btn btn-primary"
                            disabled={!customUrl || loading}
                        >
                            📥 Import Data
                        </button>
                    </div>
                </div>

                {/* Preview Panel */}
                {previewData && (
                    <div className="card" style={{ marginBottom: 'var(--spacing-4)' }}>
                        <h3 className="mb-2">Data Preview (First 5 Records)</h3>
                        <div style={{ 
                            background: '#1e293b', 
                            borderRadius: '8px', 
                            padding: '1rem',
                            overflow: 'auto',
                            maxHeight: '400px'
                        }}>
                            <pre style={{ 
                                color: '#e2e8f0', 
                                margin: 0, 
                                fontSize: '0.8rem',
                                whiteSpace: 'pre-wrap'
                            }}>
                                {JSON.stringify(previewData, null, 2)}
                            </pre>
                        </div>
                    </div>
                )}

                {/* Import Result */}
                {importResult && (
                    <div className="card" style={{
                        background: importResult.success ? '#ecfdf5' : '#fef2f2',
                        borderColor: importResult.success ? '#10b981' : '#ef4444'
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                            <span style={{ fontSize: '1.5rem' }}>
                                {importResult.success ? '✅' : '❌'}
                            </span>
                            <div>
                                <strong style={{ color: importResult.success ? '#065f46' : '#991b1b' }}>
                                    {importResult.success ? 'Import Successful!' : 'Import Failed'}
                                </strong>
                                <p style={{ margin: '0.25rem 0 0 0', color: importResult.success ? '#047857' : '#b91c1c' }}>
                                    {importResult.message}
                                </p>
                                {importResult.records_added !== undefined && (
                                    <div style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
                                        <span style={{ marginRight: '1rem' }}>📥 Added: {importResult.records_added}</span>
                                        <span style={{ marginRight: '1rem' }}>🔄 Updated: {importResult.records_updated || 0}</span>
                                        <span>📊 Total Processed: {importResult.total_items_processed || 0}</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                )}

                {/* JSON Format Reference */}
                <div className="card">
                    <h3 className="mb-2">📋 Supported JSON Formats</h3>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
                        The system automatically maps these common field names to inventory fields:
                    </p>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
                        <div style={{ background: 'var(--bg-secondary)', borderRadius: '8px', padding: '1rem' }}>
                            <strong style={{ color: 'var(--accent-primary)' }}>Product Fields</strong>
                            <ul style={{ margin: '0.5rem 0 0 0', paddingLeft: '1.25rem', fontSize: '0.85rem' }}>
                                <li><code>sku</code>, <code>id</code>, <code>product_id</code>, <code>code</code> → SKU</li>
                                <li><code>name</code>, <code>title</code>, <code>product_name</code> → Name</li>
                                <li><code>category</code>, <code>type</code> → Category</li>
                                <li><code>price</code>, <code>unit_price</code>, <code>cost</code> → Price</li>
                                <li><code>stock</code>, <code>quantity</code>, <code>inventory</code> → Stock</li>
                            </ul>
                        </div>
                        
                        <div style={{ background: 'var(--bg-secondary)', borderRadius: '8px', padding: '1rem' }}>
                            <strong style={{ color: 'var(--accent-success)' }}>Extra Columns (Generated)</strong>
                            <ul style={{ margin: '0.5rem 0 0 0', paddingLeft: '1.25rem', fontSize: '0.85rem' }}>
                                <li><code>supplier</code> - Vendor/supplier name</li>
                                <li><code>warehouse_location</code> - Storage location</li>
                                <li><code>min_order_qty</code> - Minimum order quantity</li>
                                <li><code>max_stock_level</code> - Maximum stock capacity</li>
                                <li><code>brand</code> - Product brand</li>
                                <li><code>weight_kg</code> - Product weight</li>
                            </ul>
                        </div>
                    </div>
                    
                    <div style={{ marginTop: '1rem', background: '#1e293b', borderRadius: '8px', padding: '1rem' }}>
                        <strong style={{ color: '#94a3b8' }}>Example JSON Format:</strong>
                        <pre style={{ color: '#e2e8f0', margin: '0.5rem 0 0 0', fontSize: '0.8rem' }}>{`[
  {
    "sku": "PROD-001",
    "name": "Wireless Mouse",
    "category": "Electronics",
    "price": 29.99,
    "stock": 150,
    "supplier": "TechSupply Co",
    "warehouse_location": "A-12-3",
    "brand": "Logitech"
  }
]`}</pre>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ApiIntegration;
