import React, { useEffect, useState, useCallback, useRef } from 'react';
import apiService, { thresholdService } from '../services/api';
import { triggerRefresh, onRefresh } from '../services/refreshService';

const ProductsDetail = () => {
  const [data, setData] = useState(null);
  const [allProducts, setAllProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [filterCategory, setFilterCategory] = useState('All');
  const [filterStock, setFilterStock] = useState('All');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalCount, setTotalCount] = useState(0);
  const [categories, setCategories] = useState(['All']);
  const pageSize = 50;
  const searchTimeout = useRef(null);
  
  // Threshold configuration state
  const [thresholds, setThresholds] = useState({
    low_stock_max: 50,
    medium_stock_max: 100
  });
  const [tempThresholds, setTempThresholds] = useState({
    low_stock_max: 50,
    medium_stock_max: 100
  });
  const [showThresholdConfig, setShowThresholdConfig] = useState(false);
  const [thresholdError, setThresholdError] = useState('');

  useEffect(() => {
    fetchData();
  }, []);

  // Debounce search term
  useEffect(() => {
    if (searchTimeout.current) clearTimeout(searchTimeout.current);
    searchTimeout.current = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 300);
    return () => clearTimeout(searchTimeout.current);
  }, [searchTerm]);

  // Fetch products when filters or page changes (using debounced search)
  useEffect(() => {
    fetchProducts();
  }, [currentPage, filterCategory, filterStock, debouncedSearch]);

  // Listen for data refresh events from other components
  useEffect(() => {
    const cleanup = onRefresh((data) => {
      console.log('ProductsDetail refreshing due to:', data.source);
      fetchData();
      fetchProducts();
    });
    return cleanup;
  }, []);

  const fetchData = async () => {
    try {
      // Fetch thresholds first
      const thresholdResponse = await thresholdService.getThresholds();
      const currentThresholds = thresholdResponse.data.thresholds;
      setThresholds(currentThresholds);
      setTempThresholds(currentThresholds);
      
      // Fetch products overview with thresholds and categories
      const [detailResponse, categoriesResponse] = await Promise.all([
        thresholdService.getProductsWithThresholds(currentThresholds.low_stock_max, currentThresholds.medium_stock_max),
        apiService.get('/products/categories')
      ]);
      setData(detailResponse.data);
      if (categoriesResponse.data) {
        setCategories(['All', ...categoriesResponse.data]);
      }
    } catch (error) {
      console.error('Error fetching products detail:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchProducts = async () => {
    try {
      // Use paginated endpoint for fast loading
      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: pageSize.toString()
      });
      if (filterCategory && filterCategory !== 'All') params.append('category', filterCategory);
      if (filterStock && filterStock !== 'All') params.append('stock_filter', filterStock);
      if (debouncedSearch) params.append('search', debouncedSearch);
      
      const response = await apiService.get(`/products/paginated?${params.toString()}`);
      setAllProducts(response.data.products || []);
      setTotalCount(response.data.total_count || 0);
    } catch (error) {
      console.error('Error fetching products:', error);
    }
  };

  const handleApplyThresholds = async () => {
    // Validate
    if (tempThresholds.low_stock_max >= tempThresholds.medium_stock_max) {
      setThresholdError('Low Stock threshold must be less than Medium Stock threshold');
      return;
    }
    if (tempThresholds.low_stock_max < 0 || tempThresholds.medium_stock_max < 0) {
      setThresholdError('Thresholds must be non-negative');
      return;
    }
    
    setThresholdError('');
    
    try {
      // Update thresholds on server
      await thresholdService.updateThresholds(tempThresholds);
      setThresholds(tempThresholds);
      
      // Refetch data with new thresholds
      const detailResponse = await thresholdService.getProductsWithThresholds(
        tempThresholds.low_stock_max, 
        tempThresholds.medium_stock_max
      );
      setData(detailResponse.data);
      
      // Refresh products list
      await fetchProducts();
      
      // Trigger global refresh to update dashboard and all other components
      triggerRefresh('threshold-update');
      
      setShowThresholdConfig(false);
    } catch (error) {
      setThresholdError(error.response?.data?.detail || 'Failed to update thresholds');
    }
  };

  const getStockStatus = (stock) => {
    if (stock === 0) return { label: 'Out of Stock', color: '#991b1b', bg: '#fee2e2' };
    if (stock <= thresholds.low_stock_max) return { label: 'Low Stock', color: '#92400e', bg: '#fef3c7' };
    if (stock <= thresholds.medium_stock_max) return { label: 'Medium Stock', color: '#166534', bg: '#e5f0e5' };
    return { label: 'High Stock', color: '#1e40af', bg: '#e8f0f8' };
  };

  if (loading) {
    return <div style={{ textAlign: 'center', padding: '40px' }}>Loading...</div>;
  }

  if (!data) {
    return <div style={{ textAlign: 'center', padding: '40px' }}>No data available</div>;
  }

  // Use products directly (server-side filtering is applied)
  const filteredProducts = allProducts;
  const totalPages = Math.ceil(totalCount / pageSize);

  return (
    <div>
      {/* Products Overview - Merged Section */}
      <div className="detail-section" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ margin: 0 }}>📊 Products Overview</h3>
          <button
            onClick={() => setShowThresholdConfig(!showThresholdConfig)}
            style={{
              padding: '8px 16px',
              background: showThresholdConfig ? '#3b82f6' : '#f3f4f6',
              color: showThresholdConfig ? 'white' : '#374151',
              border: '1px solid #e5e7eb',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: '500',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            ⚙️ Configure Thresholds
          </button>
        </div>

        {/* Threshold Configuration Panel */}
        {showThresholdConfig && (
          <div style={{
            background: '#f8fafc',
            border: '1px solid #e2e8f0',
            borderRadius: '8px',
            padding: '20px',
            marginBottom: '20px'
          }}>
            <h4 style={{ margin: '0 0 16px 0', color: '#1e293b' }}>📐 Stock Classification Thresholds</h4>
            <p style={{ color: '#64748b', fontSize: '13px', marginBottom: '16px' }}>
              Customize how stock levels are classified. Changes will recalculate all product statuses.
            </p>
            
            <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap', marginBottom: '16px' }}>
              <div style={{ flex: 1, minWidth: '200px' }}>
                <label style={{ display: 'block', marginBottom: '6px', fontWeight: '500', color: '#334155', fontSize: '13px' }}>
                  🟠 Low Stock (≤ units)
                </label>
                <input
                  type="number"
                  min="0"
                  value={tempThresholds.low_stock_max}
                  onChange={(e) => setTempThresholds({...tempThresholds, low_stock_max: parseInt(e.target.value) || 0})}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    border: '1px solid #e2e8f0',
                    borderRadius: '6px',
                    fontSize: '14px'
                  }}
                />
                <span style={{ fontSize: '12px', color: '#64748b' }}>Products with stock ≤ {tempThresholds.low_stock_max} = Low Stock</span>
              </div>
              
              <div style={{ flex: 1, minWidth: '200px' }}>
                <label style={{ display: 'block', marginBottom: '6px', fontWeight: '500', color: '#334155', fontSize: '13px' }}>
                  🟢 Medium Stock (≤ units)
                </label>
                <input
                  type="number"
                  min="0"
                  value={tempThresholds.medium_stock_max}
                  onChange={(e) => setTempThresholds({...tempThresholds, medium_stock_max: parseInt(e.target.value) || 0})}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    border: '1px solid #e2e8f0',
                    borderRadius: '6px',
                    fontSize: '14px'
                  }}
                />
                <span style={{ fontSize: '12px', color: '#64748b' }}>Products with stock ≤ {tempThresholds.medium_stock_max} = Medium Stock</span>
              </div>
              
              <div style={{ flex: 1, minWidth: '200px' }}>
                <label style={{ display: 'block', marginBottom: '6px', fontWeight: '500', color: '#334155', fontSize: '13px' }}>
                  🔵 High Stock (&gt; units)
                </label>
                <input
                  type="number"
                  value={tempThresholds.medium_stock_max}
                  disabled
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    border: '1px solid #e2e8f0',
                    borderRadius: '6px',
                    fontSize: '14px',
                    background: '#f1f5f9',
                    color: '#64748b'
                  }}
                />
                <span style={{ fontSize: '12px', color: '#64748b' }}>Products with stock &gt; {tempThresholds.medium_stock_max} = High Stock</span>
              </div>
            </div>
            
            {thresholdError && (
              <div style={{ color: '#dc2626', fontSize: '13px', marginBottom: '12px', padding: '8px', background: '#fef2f2', borderRadius: '4px' }}>
                ⚠️ {thresholdError}
              </div>
            )}
            
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={handleApplyThresholds}
                style={{
                  padding: '10px 20px',
                  background: '#10b981',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: '500',
                  fontSize: '14px'
                }}
              >
                ✓ Apply Thresholds
              </button>
              <button
                onClick={() => {
                  setTempThresholds(thresholds);
                  setShowThresholdConfig(false);
                  setThresholdError('');
                }}
                style={{
                  padding: '10px 20px',
                  background: '#f1f5f9',
                  color: '#475569',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  cursor: 'pointer',
                  fontWeight: '500',
                  fontSize: '14px'
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Summary + Stock Distribution Combined */}
        <div className="detail-grid">
          <div className="detail-card">
            <div className="detail-card-label">Total Products</div>
            <div className="detail-card-value">{data.total_products}</div>
          </div>
          <div className="detail-card">
            <div className="detail-card-label">Categories</div>
            <div className="detail-card-value">{data.category_breakdown.length}</div>
          </div>
          <div className="detail-card">
            <div className="detail-card-label" style={{ color: '#991b1b' }}>🔴 Out of Stock</div>
            <div className="detail-card-value" style={{ color: '#b84444' }}>
              {data.stock_distribution.out_of_stock}
            </div>
            <div className="detail-card-subtitle">Stock = 0</div>
          </div>
          <div className="detail-card">
            <div className="detail-card-label" style={{ color: '#92400e' }}>🟠 Low Stock</div>
            <div className="detail-card-value" style={{ color: '#ea580c' }}>
              {data.stock_distribution.low_stock}
            </div>
            <div className="detail-card-subtitle">≤ {thresholds.low_stock_max} units</div>
          </div>
        </div>
        
        <div className="detail-grid" style={{ marginTop: '12px' }}>
          <div className="detail-card">
            <div className="detail-card-label" style={{ color: '#166534' }}>🟢 Medium Stock</div>
            <div className="detail-card-value" style={{ color: '#16a34a' }}>
              {data.stock_distribution.medium_stock}
            </div>
            <div className="detail-card-subtitle">{thresholds.low_stock_max + 1} - {thresholds.medium_stock_max} units</div>
          </div>
          <div className="detail-card">
            <div className="detail-card-label" style={{ color: '#1e40af' }}>🔵 High Stock</div>
            <div className="detail-card-value" style={{ color: '#2563eb' }}>
              {data.stock_distribution.high_stock}
            </div>
            <div className="detail-card-subtitle">&gt; {thresholds.medium_stock_max} units</div>
          </div>
          <div className="detail-card" style={{ gridColumn: 'span 2' }}>
            <div className="detail-card-label">Current Thresholds</div>
            <div style={{ fontSize: '13px', color: '#64748b', marginTop: '8px' }}>
              <span style={{ marginRight: '16px' }}>Low: ≤ <strong>{thresholds.low_stock_max}</strong></span>
              <span style={{ marginRight: '16px' }}>Medium: ≤ <strong>{thresholds.medium_stock_max}</strong></span>
              <span>High: &gt; <strong>{thresholds.medium_stock_max}</strong></span>
            </div>
          </div>
        </div>
      </div>

      {/* Category Breakdown */}
      <div className="detail-section">
        <h3>📦 Products by Category</h3>
        <table className="detail-table">
          <thead>
            <tr>
              <th>Category</th>
              <th>Products</th>
              <th>Total Stock</th>
              <th>Total Value</th>
            </tr>
          </thead>
          <tbody>
            {data.category_breakdown.map((cat, idx) => (
              <tr key={idx}>
                <td><strong>{cat.category}</strong></td>
                <td>{cat.count}</td>
                <td>{cat.total_stock.toLocaleString()} units</td>
                <td>${cat.total_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* All Products List */}
      <div className="detail-section">
        <h3>📋 All Products ({totalCount.toLocaleString()} total)</h3>
        
        {/* Filters */}
        <div style={{ 
          display: 'flex', 
          gap: '16px', 
          marginBottom: '16px',
          flexWrap: 'wrap'
        }}>
          <input
            type="text"
            placeholder="🔍 Search by name or SKU..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            style={{
              flex: 1,
              minWidth: '250px',
              padding: '12px 16px',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              fontSize: '14px'
            }}
          />
          <select
            value={filterCategory}
            onChange={(e) => {
              setFilterCategory(e.target.value);
              setCurrentPage(1);
            }}
            style={{
              padding: '12px 16px',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              fontSize: '14px',
              backgroundColor: 'white'
            }}
          >
            {categories.map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
          <select
            value={filterStock}
            onChange={(e) => {
              setFilterStock(e.target.value);
              setCurrentPage(1);
            }}
            style={{
              padding: '12px 16px',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              fontSize: '14px',
              backgroundColor: 'white'
            }}
          >
            <option value="All">All Stock Levels</option>
            <option value="Out of Stock">Out of Stock (= 0)</option>
            <option value="Low Stock">Low Stock (≤ {thresholds.low_stock_max})</option>
            <option value="Medium Stock">Medium Stock ({thresholds.low_stock_max + 1}-{thresholds.medium_stock_max})</option>
            <option value="High Stock">High Stock (&gt; {thresholds.medium_stock_max})</option>
          </select>
        </div>

        {/* Products Table */}
        <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
          <table className="detail-table">
            <thead style={{ position: 'sticky', top: 0, zIndex: 10 }}>
              <tr>
                <th>SKU</th>
                <th>Product Name</th>
                <th>Category</th>
                <th>Current Stock</th>
                <th>Status</th>
                <th>Unit Price</th>
                <th>Stock Value</th>
                <th>Reorder Point</th>
                <th>Avg Daily Demand</th>
              </tr>
            </thead>
            <tbody>
              {filteredProducts.map((product, idx) => {
                const status = getStockStatus(product.current_stock);
                return (
                  <tr key={idx}>
                    <td><strong>{product.sku}</strong></td>
                    <td>{product.name}</td>
                    <td>{product.category}</td>
                    <td>{product.current_stock.toLocaleString()} units</td>
                    <td>
                      <span style={{
                        padding: '4px 12px',
                        borderRadius: '12px',
                        fontSize: '12px',
                        fontWeight: '600',
                        backgroundColor: status.bg,
                        color: status.color
                      }}>
                        {status.label}
                      </span>
                    </td>
                    <td>${product.unit_price.toFixed(2)}</td>
                    <td><strong>${(product.current_stock * product.unit_price).toLocaleString()}</strong></td>
                    <td>{product.reorder_point} units</td>
                    <td>{product.average_daily_demand} units/day</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {filteredProducts.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">🔍</div>
            <div className="empty-state-text">
              No products match your filters
            </div>
          </div>
        )}

        {/* Pagination Controls */}
        {totalPages > 1 && (
          <div style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center', 
            marginTop: '16px',
            padding: '12px 0',
            borderTop: '1px solid #e5e7eb'
          }}>
            <div style={{ color: '#6b7280', fontSize: '14px' }}>
              Showing {((currentPage - 1) * pageSize) + 1} - {Math.min(currentPage * pageSize, totalCount)} of {totalCount.toLocaleString()} products
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button
                onClick={() => setCurrentPage(1)}
                disabled={currentPage === 1}
                style={{
                  padding: '8px 12px',
                  border: '1px solid #e5e7eb',
                  borderRadius: '6px',
                  background: currentPage === 1 ? '#f3f4f6' : 'white',
                  cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                  color: currentPage === 1 ? '#9ca3af' : '#374151'
                }}
              >
                ⟪ First
              </button>
              <button
                onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                style={{
                  padding: '8px 12px',
                  border: '1px solid #e5e7eb',
                  borderRadius: '6px',
                  background: currentPage === 1 ? '#f3f4f6' : 'white',
                  cursor: currentPage === 1 ? 'not-allowed' : 'pointer',
                  color: currentPage === 1 ? '#9ca3af' : '#374151'
                }}
              >
                ← Prev
              </button>
              <span style={{ padding: '0 12px', fontWeight: '500' }}>
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                style={{
                  padding: '8px 12px',
                  border: '1px solid #e5e7eb',
                  borderRadius: '6px',
                  background: currentPage === totalPages ? '#f3f4f6' : 'white',
                  cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                  color: currentPage === totalPages ? '#9ca3af' : '#374151'
                }}
              >
                Next →
              </button>
              <button
                onClick={() => setCurrentPage(totalPages)}
                disabled={currentPage === totalPages}
                style={{
                  padding: '8px 12px',
                  border: '1px solid #e5e7eb',
                  borderRadius: '6px',
                  background: currentPage === totalPages ? '#f3f4f6' : 'white',
                  cursor: currentPage === totalPages ? 'not-allowed' : 'pointer',
                  color: currentPage === totalPages ? '#9ca3af' : '#374151'
                }}
              >
                Last ⟫
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Top Products by Value */}
      {data.top_by_value && data.top_by_value.length > 0 && (
        <div className="detail-section">
          <h3>💰 Top 10 Products by Stock Value</h3>
          <table className="detail-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Product Name</th>
                <th>Category</th>
                <th>Stock</th>
                <th>Value</th>
              </tr>
            </thead>
            <tbody>
              {data.top_by_value.map((product, idx) => (
                <tr key={idx}>
                  <td><strong>{product.sku}</strong></td>
                  <td>{product.name}</td>
                  <td>{product.category}</td>
                  <td>{product.stock.toLocaleString()} units</td>
                  <td><strong>${product.value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</strong></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ProductsDetail;
