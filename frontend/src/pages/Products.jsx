import React, { useState, useEffect } from 'react';
import { productService, dataService, thresholdService, emailService } from '../services/api';
import { triggerRefresh } from '../services/refreshService';
import Modal from '../components/Modal';
import ProductInsightModal from '../components/ProductInsightModal';
import EmailAlertModal from '../components/EmailAlertModal';

const Products = () => {
    const [products, setProducts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [selectedProduct, setSelectedProduct] = useState(null);
    const [uploadMode, setUploadMode] = useState(null); // 'new', 'restock', or 'sales'
    const [uploadProgress, setUploadProgress] = useState(null); // Track upload progress
    const [uploadFileSize, setUploadFileSize] = useState(null); // Track file size
    const [showUploadDropdown, setShowUploadDropdown] = useState(false);
    const [restockPreview, setRestockPreview] = useState(null);
    const [showRestockModal, setShowRestockModal] = useState(false);
    const [duplicateError, setDuplicateError] = useState(null);
    const [stockFilter, setStockFilter] = useState(null);
    const [selectedRestockItems, setSelectedRestockItems] = useState([]);
    const [showAllCritical, setShowAllCritical] = useState(false);
    const [showAllHighRisk, setShowAllHighRisk] = useState(false);
    const [showEmailModal, setShowEmailModal] = useState(false);
    // Configurable thresholds
    const [thresholds, setThresholds] = useState({ low_stock_max: 50, medium_stock_max: 100 });
    
    // Ordering recommendations state (loaded separately from paginated products)
    const [orderingRecs, setOrderingRecs] = useState(null);
    
    // Pagination state
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize] = useState(50);
    const [totalCount, setTotalCount] = useState(0);
    const [totalPages, setTotalPages] = useState(0);
    const [summary, setSummary] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    
    // Threshold alert state
    const [thresholdAlerts, setThresholdAlerts] = useState(null);
    const [showThresholdAlert, setShowThresholdAlert] = useState(false);
    const [alertEmailTo, setAlertEmailTo] = useState('');
    const [sendingAlert, setSendingAlert] = useState(false);

    useEffect(() => {
        loadThresholdsAndSummary();
        loadOrderingRecommendations();
    }, []);
    
    useEffect(() => {
        loadProducts();
    }, [currentPage, stockFilter, searchTerm]);

    const loadOrderingRecommendations = async () => {
        try {
            const response = await productService.getOrderingRecommendations();
            setOrderingRecs(response.data);
        } catch (error) {
            console.error('Error loading ordering recommendations:', error);
        }
    };

    const loadThresholdsAndSummary = async () => {
        try {
            const [thresholdResponse, summaryResponse] = await Promise.all([
                thresholdService.getThresholds(),
                productService.getSummary()
            ]);
            setThresholds(thresholdResponse.data.thresholds);
            setSummary(summaryResponse.data);
            // Alerts are now shown on Dashboard, not as popup
        } catch (error) {
            console.error('Error loading thresholds/summary:', error);
        }
    };

    const loadProducts = async () => {
        setLoading(true);
        try {
            const response = await productService.getPaginated(currentPage, pageSize, {
                stockFilter: stockFilter,
                search: searchTerm || undefined
            });
            setProducts(response.data.products);
            setTotalCount(response.data.pagination.total_count);
            setTotalPages(response.data.pagination.total_pages);
        } catch (error) {
            console.error('Error loading products:', error);
        } finally {
            setLoading(false);
        }
    };

    const checkThresholdAlerts = async () => {
        try {
            const response = await emailService.checkThresholdAlerts();
            if (response.data.has_alerts) {
                setThresholdAlerts(response.data);
                setShowThresholdAlert(true);
            }
        } catch (error) {
            console.error('Error checking threshold alerts:', error);
        }
    };

    const handleSendThresholdEmail = async () => {
        if (!alertEmailTo || !alertEmailTo.includes('@')) {
            alert('Please enter a valid email address');
            return;
        }
        
        setSendingAlert(true);
        try {
            const alertIds = thresholdAlerts?.alerts?.map(a => a.id) || [];
            const response = await emailService.sendThresholdEmail(alertEmailTo, alertIds);
            alert(`Email sent to ${alertEmailTo}!\n\n${response.data.message}`);
            setShowThresholdAlert(false);
            setAlertEmailTo('');
        } catch (error) {
            alert('Failed to prepare email: ' + (error.response?.data?.detail || error.message));
        } finally {
            setSendingAlert(false);
        }
    };

    const handleFileUpload = async (event, mode) => {
        const file = event.target.files[0];
        if (!file) return;

        // Check file size and warn for large files
        const fileSizeMB = file.size / (1024 * 1024);
        setUploadFileSize(fileSizeMB);
        
        if (fileSizeMB > 100 && mode === 'sales') {
            // OPTIMIZED: With index management, uploads are 50-100x faster
            // Calculation: File processing + index recreation time
            let estimatedSeconds;
            if (fileSizeMB > 500) {
                estimatedSeconds = Math.ceil(60 + (fileSizeMB - 500) / 10); // 1+ minutes
            } else if (fileSizeMB > 300) {
                estimatedSeconds = Math.ceil(45 + (fileSizeMB - 300) / 15); // 45-60 seconds
            } else {
                estimatedSeconds = Math.ceil(30 + fileSizeMB / 10); // 30-45 seconds
            }
            
            const estimatedMinutes = estimatedSeconds >= 60 
                ? `${Math.floor(estimatedSeconds / 60)}m ${estimatedSeconds % 60}s`
                : `${estimatedSeconds} seconds`;
            
            const proceed = window.confirm(
                `⚠️ LARGE FILE DETECTED\n\n` +
                `File size: ${fileSizeMB.toFixed(1)} MB\n` +
                `Estimated time: ${estimatedMinutes}\n\n` +
                `Upload optimized with index management.\n` +
                `Progress will be shown in backend console.\n\n` +
                `Continue?`
            );
            if (!proceed) {
                event.target.value = '';
                return;
            }
        }

        setUploading(true);
        setUploadMode(mode);
        setUploadProgress('Uploading file...');
        setDuplicateError(null);
        setRestockPreview(null);
        
        // Start timer for progress estimation
        const startTime = Date.now();
        
        try {
            if (mode === 'new') {
                // Upload new products only - rejects duplicates
                await dataService.uploadNewProducts(file);
                alert('New products uploaded successfully!');
                triggerRefresh('new-products');
                loadProducts();
                loadOrderingRecommendations();
                // Check for threshold alerts after adding new products
                checkThresholdAlerts();
            } else if (mode === 'restock') {
                // Restock existing products - shows preview
                const response = await dataService.restockInventory(file);
                setRestockPreview(response.data);
                // Select all items by default
                setSelectedRestockItems(response.data.restock_items.map(item => item.sku));
                setShowRestockModal(true);
            } else if (mode === 'sales') {
                // Upload sales history data - use fast endpoint
                setUploadProgress('Processing sales data...');
                const response = await dataService.uploadSalesFast(file);
                const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
                const msg = response.data.message || 'Sales history uploaded successfully!';
                const details = (
                    `✅ ${msg}\n\n` +
                    `Time taken: ${elapsed} seconds\n` +
                    `Records added: ${response.data.records_added?.toLocaleString() || 'N/A'}\n` +
                    `Processing speed: ${response.data.records_per_second?.toLocaleString() || 'N/A'} records/sec`
                );
                alert(details);
                triggerRefresh('sales-history');
                // Don't reload all products for sales upload - just refresh summary
                loadThresholdsAndSummary();
                loadOrderingRecommendations();
            }
        } catch (error) {
            console.error('Error uploading file:', error);
            
            if (error.response?.status === 409 && mode === 'new') {
                // Duplicate products found
                setDuplicateError(error.response.data.detail);
            } else {
                alert(`Error uploading file: ${error.response?.data?.detail || error.message}`);
            }
        } finally {
            setUploading(false);
            setUploadProgress(null);
            setUploadFileSize(null);
            event.target.value = ''; // Reset file input
        }
    };

    const handleConfirmRestock = async () => {
        try {
            // Only restock selected items
            const items = restockPreview.restock_items
                .filter(item => selectedRestockItems.includes(item.sku))
                .map(item => ({
                    sku: item.sku,
                    restock_quantity: item.restock_quantity
                }));
            
            if (items.length === 0) {
                alert('Please select at least one product to restock');
                return;
            }
            
            await dataService.confirmRestock({ items });
            alert(`Successfully restocked ${items.length} products!`);
            setShowRestockModal(false);
            setRestockPreview(null);
            setSelectedRestockItems([]);
            triggerRefresh('restock');
            loadProducts();
            loadOrderingRecommendations();
        } catch (error) {
            console.error('Error confirming restock:', error);
            alert('Error completing restock operation');
        }
    };

    const getRiskBadgeClass = (risk) => {
        switch (risk) {
            case 'CRITICAL':
                return 'badge-danger';
            case 'HIGH':
                return 'badge-warning';
            case 'MEDIUM':
                return 'badge-info';
            case 'LOW':
                return 'badge-success';
            default:
                return 'badge-info';
        }
    };

    const getStockLevelCategory = (stock) => {
        if (stock === 0) return { label: 'OUT', color: '#ef4444', bg: '#fee2e2' };
        if (stock <= thresholds.low_stock_max) return { label: 'LOW', color: '#8b6914', bg: '#f5f2e8' };
        if (stock <= thresholds.medium_stock_max) return { label: 'MEDIUM', color: '#4a8055', bg: '#e5f0e5' };
        return { label: 'HIGH', color: '#3b82f6', bg: '#dbeafe' };
    };

    const getStockStats = () => {
        // Use server-side summary for fast loading
        if (summary) {
            return {
                outOfStock: summary.stock_distribution.out_of_stock,
                lowStock: summary.stock_distribution.low_stock,
                mediumStock: summary.stock_distribution.medium_stock,
                highStock: summary.stock_distribution.high_stock,
            };
        }
        return { outOfStock: 0, lowStock: 0, mediumStock: 0, highStock: 0 };
    };

    const getFilteredProducts = () => {
        // Products are already filtered server-side
        return products;
    };

    const handleStockFilterClick = (filter) => {
        const newFilter = stockFilter === filter ? null : filter;
        setStockFilter(newFilter);
        setCurrentPage(1); // Reset to first page when filter changes
    };
    
    const handleSearch = (e) => {
        setSearchTerm(e.target.value);
        setCurrentPage(1); // Reset to first page when searching
    };

    if (loading) {
        return (
            <div className="page-container">
                <div className="container">
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
                        <div className="spinner"></div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="page-container">
            <div className="container">
                {/* Page Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
                    <div>
                        <h1 style={{ fontSize: '1.75rem', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>Product Inventory</h1>
                        <p style={{ color: 'var(--text-tertiary)', fontSize: '0.9rem' }}>Manage and monitor your product stock levels</p>
                    </div>
                    <div style={{ display: 'flex', gap: 'var(--spacing-3)', alignItems: 'center' }}>
                        {/* Consolidated Upload Dropdown */}
                        <div style={{ position: 'relative' }}>
                            <button 
                                onClick={() => setShowUploadDropdown(!showUploadDropdown)}
                                className="btn btn-primary"
                                style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
                                disabled={uploading}
                            >
                                {uploading ? (
                                    <>
                                        <svg className="spinner" width="16" height="16" viewBox="0 0 24 24">
                                            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" fill="none"/>
                                        </svg>
                                        {uploadProgress || (uploadMode === 'new' ? 'Uploading Products...' : uploadMode === 'sales' ? 'Uploading Sales...' : 'Processing Restock...')}
                                        {uploadFileSize && uploadFileSize > 50 && (
                                            <div style={{ fontSize: '12px', marginTop: '8px', opacity: 0.8 }}>
                                                File size: {uploadFileSize.toFixed(1)} MB - This may take a few minutes...
                                            </div>
                                        )}
                                    </>
                                ) : (
                                    <>
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                        </svg>
                                        Upload Data
                                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                                            <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                                        </svg>
                                    </>
                                )}
                            </button>
                            {showUploadDropdown && !uploading && (
                                <div style={{
                                    position: 'absolute',
                                    top: '100%',
                                    right: 0,
                                    marginTop: '4px',
                                    background: 'white',
                                    borderRadius: '8px',
                                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                                    border: '1px solid #e5e7eb',
                                    zIndex: 1000,
                                    minWidth: '200px',
                                    overflow: 'hidden'
                                }}>
                                    <label htmlFor="file-upload-new" style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '10px',
                                        padding: '12px 16px',
                                        cursor: 'pointer',
                                        borderBottom: '1px solid #f3f4f6',
                                        transition: 'background 0.2s'
                                    }} onMouseOver={e => e.currentTarget.style.background='#f9fafb'} onMouseOut={e => e.currentTarget.style.background='white'}>
                                        📦 Upload New Products
                                    </label>
                                    <label htmlFor="file-upload-sales" style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '10px',
                                        padding: '12px 16px',
                                        cursor: 'pointer',
                                        borderBottom: '1px solid #f3f4f6',
                                        transition: 'background 0.2s'
                                    }} onMouseOver={e => e.currentTarget.style.background='#f9fafb'} onMouseOut={e => e.currentTarget.style.background='white'}>
                                        📊 Upload Sales CSV
                                    </label>
                                    <label htmlFor="file-upload-restock" style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '10px',
                                        padding: '12px 16px',
                                        cursor: 'pointer',
                                        transition: 'background 0.2s'
                                    }} onMouseOver={e => e.currentTarget.style.background='#f9fafb'} onMouseOut={e => e.currentTarget.style.background='white'}>
                                        📥 Restock Inventory
                                    </label>
                                </div>
                            )}
                            {/* Hidden file inputs */}
                            <input id="file-upload-new" type="file" accept=".csv,.xlsx,.xls,.json" onChange={(e) => { handleFileUpload(e, 'new'); setShowUploadDropdown(false); }} style={{ display: 'none' }} disabled={uploading} />
                            <input id="file-upload-sales" type="file" accept=".csv" onChange={(e) => { handleFileUpload(e, 'sales'); setShowUploadDropdown(false); }} style={{ display: 'none' }} disabled={uploading} />
                            <input id="file-upload-restock" type="file" accept=".csv,.xlsx,.xls,.json" onChange={(e) => { handleFileUpload(e, 'restock'); setShowUploadDropdown(false); }} style={{ display: 'none' }} disabled={uploading} />
                        </div>
                    </div>
                </div>

                {products.length === 0 ? (
                    <div className="card text-center" style={{ padding: 'var(--spacing-12)' }}>
                        <svg width="64" height="64" viewBox="0 0 24 24" fill="none" style={{ margin: '0 auto var(--spacing-4)', color: 'var(--color-gray-300)' }}>
                            <rect x="3" y="3" width="18" height="18" rx="2" stroke="currentColor" strokeWidth="2"/>
                            <path d="M3 9h18M9 21V9" stroke="currentColor" strokeWidth="2"/>
                        </svg>
                        <h3 style={{ marginBottom: 'var(--spacing-2)' }}>No Products Found</h3>
                        <p style={{ color: 'var(--text-secondary)', marginTop: 'var(--spacing-2)' }}>
                            Upload sales data to get started with inventory optimization
                        </p>
                    </div>
                ) : (
                    <>
                        {/* Stock Summary */}
                        <div className="grid grid-4 mb-4">
                            <div className="card" 
                                onClick={() => handleStockFilterClick('OUT')}
                                style={{ 
                                    background: '#ffffff',
                                    borderLeft: `3px solid ${stockFilter === 'OUT' ? '#ef4444' : '#fca5a5'}`,
                                    border: stockFilter === 'OUT' ? '1px solid #e5e7eb' : '1px solid #f1f5f9',
                                    borderLeftWidth: '3px',
                                    borderLeftStyle: 'solid',
                                    borderLeftColor: '#ef4444',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                    boxShadow: stockFilter === 'OUT' ? '0 2px 8px rgba(0,0,0,0.06)' : '0 1px 3px rgba(0,0,0,0.03)'
                                }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.3px', marginBottom: '0.4rem' }}>Out of Stock</div>
                                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#1e293b' }}>
                                    {getStockStats().outOfStock}
                                </div>
                            </div>
                            <div className="card" 
                                onClick={() => handleStockFilterClick('LOW')}
                                style={{ 
                                    background: '#ffffff',
                                    border: stockFilter === 'LOW' ? '1px solid #e5e7eb' : '1px solid #f1f5f9',
                                    borderLeftWidth: '3px',
                                    borderLeftStyle: 'solid',
                                    borderLeftColor: '#f59e0b',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                    boxShadow: stockFilter === 'LOW' ? '0 2px 8px rgba(0,0,0,0.06)' : '0 1px 3px rgba(0,0,0,0.03)'
                                }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.3px', marginBottom: '0.4rem' }}>Low Stock</div>
                                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#1e293b' }}>
                                    {getStockStats().lowStock}
                                </div>
                            </div>
                            <div className="card" 
                                onClick={() => handleStockFilterClick('MEDIUM')}
                                style={{ 
                                    background: '#ffffff',
                                    border: stockFilter === 'MEDIUM' ? '1px solid #e5e7eb' : '1px solid #f1f5f9',
                                    borderLeftWidth: '3px',
                                    borderLeftStyle: 'solid',
                                    borderLeftColor: '#0D9488',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                    boxShadow: stockFilter === 'MEDIUM' ? '0 2px 8px rgba(0,0,0,0.06)' : '0 1px 3px rgba(0,0,0,0.03)'
                                }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.3px', marginBottom: '0.4rem' }}>Medium Stock</div>
                                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#1e293b' }}>
                                    {getStockStats().mediumStock}
                                </div>
                            </div>
                            <div className="card" 
                                onClick={() => handleStockFilterClick('HIGH')}
                                style={{ 
                                    background: '#ffffff',
                                    border: stockFilter === 'HIGH' ? '1px solid #e5e7eb' : '1px solid #f1f5f9',
                                    borderLeftWidth: '3px',
                                    borderLeftStyle: 'solid',
                                    borderLeftColor: '#6366f1',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s',
                                    boxShadow: stockFilter === 'HIGH' ? '0 2px 8px rgba(0,0,0,0.06)' : '0 1px 3px rgba(0,0,0,0.03)'
                                }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.3px', marginBottom: '0.4rem' }}>High Stock</div>
                                <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#1e293b' }}>
                                    {getStockStats().highStock}
                                </div>
                            </div>
                        </div>

                        {/* Recommendations & Alerts Section */}
                        {(orderingRecs?.critical?.total_count > 0 || orderingRecs?.high_risk?.total_count > 0) && (
                            <div className="card" style={{ 
                                marginBottom: 'var(--spacing-4)', 
                                background: '#ffffff',
                                border: '1px solid #e2e8f0',
                                padding: 'var(--spacing-4)'
                            }}>
                                <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
                                    <div style={{ 
                                        width: '40px', height: '40px', borderRadius: '10px', 
                                        background: '#f0fdfa', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
                                    }}>
                                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#0D9488" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>
                                    </div>
                                    <div style={{ flex: 1 }}>
                                        <h3 style={{ 
                                            color: '#0f172a',
                                            marginBottom: '0.35rem',
                                            fontSize: '1.05rem',
                                            fontWeight: 600
                                        }}>
                                            Ordering Recommendations
                                        </h3>
                                        <p style={{ 
                                            color: '#94a3b8',
                                            marginBottom: '1.25rem',
                                            fontSize: '0.85rem'
                                        }}>
                                            Based on historical sales patterns, current inventory levels, and demand forecasting, here's what needs immediate attention:
                                        </p>
                                        
                                        {/* Critical Items - Out of Stock */}
                                        {orderingRecs?.critical?.total_count > 0 && (
                                            <div style={{ 
                                                marginBottom: '1rem',
                                                padding: '1rem',
                                                background: '#fafafa',
                                                borderRadius: '8px',
                                                border: '1px solid #e5e7eb',
                                                borderLeft: '3px solid #ef4444'
                                            }}>
                                                <h4 style={{ 
                                                    color: '#1e293b',
                                                    marginBottom: '0.75rem',
                                                    fontSize: '0.875rem',
                                                    fontWeight: 600,
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.5rem'
                                                }}>
                                                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ef4444', display: 'inline-block' }}></span>
                                                    CRITICAL: Out of Stock ({orderingRecs.critical.total_count} items)
                                                </h4>
                                                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-2)' }}>
                                                    {(showAllCritical ? orderingRecs.critical.items : orderingRecs.critical.items.slice(0, 3)).map(product => (
                                                        <div key={product.id} style={{ 
                                                            display: 'flex', 
                                                            justifyContent: 'space-between',
                                                            alignItems: 'center',
                                                            padding: '0.6rem 0.75rem',
                                                            background: '#ffffff',
                                                            borderRadius: '6px',
                                                            border: '1px solid #f1f5f9',
                                                            fontSize: '0.85rem'
                                                        }}>
                                                            <div>
                                                                <span style={{ fontWeight: 600, color: '#1e293b' }}>{product.name}</span>
                                                                <span style={{ color: '#94a3b8', marginLeft: '0.5rem', fontSize: '0.8rem' }}>
                                                                    (Avg: {product.average_daily_demand || 'N/A'} units/day)
                                                                </span>
                                                            </div>
                                                            <div style={{ 
                                                                fontWeight: 600,
                                                                color: '#0f766e',
                                                                background: '#f0fdfa',
                                                                padding: '0.35rem 0.75rem',
                                                                borderRadius: '6px',
                                                                border: '1px solid #ccfbf1',
                                                                fontSize: '0.8rem'
                                                            }}>
                                                                Order: {product.order_quantity} units
                                                            </div>
                                                        </div>
                                                    ))}
                                                    {orderingRecs.critical.items.length > 3 && !showAllCritical && (
                                                        <div 
                                                            onClick={() => setShowAllCritical(true)}
                                                            style={{ 
                                                                color: '#0D9488',
                                                                fontSize: '0.8rem',
                                                                fontWeight: 600,
                                                                textAlign: 'center',
                                                                paddingTop: '0.5rem',
                                                                cursor: 'pointer'
                                                            }}>
                                                            + {orderingRecs.critical.items.length - 3} more items need immediate ordering (click to expand)
                                                        </div>
                                                    )}
                                                    {orderingRecs.critical.total_count > orderingRecs.critical.showing_top && (
                                                        <div style={{ 
                                                            color: '#94a3b8',
                                                            fontSize: '0.75rem',
                                                            textAlign: 'center',
                                                            paddingTop: '0.25rem',
                                                            fontStyle: 'italic'
                                                        }}>
                                                            Showing top {orderingRecs.critical.showing_top} by demand priority of {orderingRecs.critical.total_count} total
                                                        </div>
                                                    )}
                                                    {showAllCritical && orderingRecs.critical.items.length > 3 && (
                                                        <div 
                                                            onClick={() => setShowAllCritical(false)}
                                                            style={{ 
                                                                color: '#0D9488',
                                                                fontSize: '0.8rem',
                                                                fontWeight: 600,
                                                                textAlign: 'center',
                                                                paddingTop: '0.5rem',
                                                                cursor: 'pointer'
                                                            }}>
                                                            Show less
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )}

                                        {/* High Risk - Low Stock Items */}
                                        {orderingRecs?.high_risk?.total_count > 0 && (
                                            <div style={{ 
                                                padding: '1rem',
                                                background: '#fafafa',
                                                borderRadius: '8px',
                                                border: '1px solid #e5e7eb',
                                                borderLeft: '3px solid #f59e0b'
                                            }}>
                                                <h4 style={{ 
                                                    color: '#1e293b',
                                                    marginBottom: '0.75rem',
                                                    fontSize: '0.875rem',
                                                    fontWeight: 600,
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.5rem'
                                                }}>
                                                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b', display: 'inline-block' }}></span>
                                                    HIGH RISK: Low Stock Alert ({orderingRecs.high_risk.total_count} items)
                                                </h4>
                                                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-2)' }}>
                                                    {(showAllHighRisk ? orderingRecs.high_risk.items : orderingRecs.high_risk.items.slice(0, 3)).map(product => (
                                                        <div key={product.id} style={{ 
                                                            display: 'flex', 
                                                            justifyContent: 'space-between',
                                                            alignItems: 'center',
                                                            padding: '0.6rem 0.75rem',
                                                            background: '#ffffff',
                                                            borderRadius: '6px',
                                                            border: '1px solid #f1f5f9',
                                                            fontSize: '0.85rem'
                                                        }}>
                                                            <div>
                                                                <span style={{ fontWeight: 600, color: '#1e293b' }}>{product.name}</span>
                                                                <span style={{ color: '#94a3b8', marginLeft: '0.5rem', fontSize: '0.8rem' }}>
                                                                    (Stock: {product.current_stock}, Days left: {product.days_left})
                                                                </span>
                                                            </div>
                                                            <div style={{ 
                                                                fontWeight: 600,
                                                                color: '#0f766e',
                                                                background: '#f0fdfa',
                                                                padding: '0.35rem 0.75rem',
                                                                borderRadius: '6px',
                                                                border: '1px solid #ccfbf1',
                                                                fontSize: '0.8rem'
                                                            }}>
                                                                Order: {product.order_quantity} units
                                                            </div>
                                                        </div>
                                                    ))}
                                                    {orderingRecs.high_risk.items.length > 3 && !showAllHighRisk && (
                                                        <div 
                                                            onClick={() => setShowAllHighRisk(true)}
                                                            style={{ 
                                                                color: '#0D9488',
                                                                fontSize: '0.8rem',
                                                                fontWeight: 600,
                                                                textAlign: 'center',
                                                                paddingTop: '0.5rem',
                                                                cursor: 'pointer'
                                                            }}>
                                                            + {orderingRecs.high_risk.items.length - 3} more items need attention (click to expand)
                                                        </div>
                                                    )}
                                                    {orderingRecs.high_risk.total_count > orderingRecs.high_risk.showing_top && (
                                                        <div style={{ 
                                                            color: '#94a3b8',
                                                            fontSize: '0.75rem',
                                                            textAlign: 'center',
                                                            paddingTop: '0.25rem',
                                                            fontStyle: 'italic'
                                                        }}>
                                                            Showing top {orderingRecs.high_risk.showing_top} by urgency of {orderingRecs.high_risk.total_count} total
                                                        </div>
                                                    )}
                                                    {showAllHighRisk && orderingRecs.high_risk.items.length > 3 && (
                                                        <div 
                                                            onClick={() => setShowAllHighRisk(false)}
                                                            style={{ 
                                                                color: '#0D9488',
                                                                fontSize: '0.8rem',
                                                                fontWeight: 600,
                                                                textAlign: 'center',
                                                                paddingTop: '0.5rem',
                                                                cursor: 'pointer'
                                                            }}>
                                                            Show less
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        )}

                                        <div style={{ 
                                            marginTop: '1rem',
                                            padding: '0.75rem 1rem',
                                            background: '#f8fafc',
                                            borderRadius: '6px',
                                            border: '1px solid #e2e8f0',
                                            fontSize: '0.8rem',
                                            color: '#64748b'
                                        }}>
                                            <strong style={{ color: '#475569' }}>How ordering works:</strong> Optimal order quantities are calculated using average demand, lead time, safety stock buffers, and Economic Order Quantity optimization. Click any product for detailed insights.
                                        </div>
                                    </div>
                                </div>
                            </div>
                        )}

                        {/* Search and Filter Toolbar */}
                        <div style={{ 
                            marginBottom: '1.25rem', 
                            display: 'flex', 
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            gap: '1rem'
                        }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1, maxWidth: '400px' }}>
                                <input
                                    type="text"
                                    placeholder="Search by SKU or product name..."
                                    value={searchTerm}
                                    onChange={(e) => handleSearch(e.target.value)}
                                    style={{
                                        flex: 1,
                                        padding: '0.6rem 0.75rem',
                                        border: '1px solid var(--border-primary)',
                                        borderRadius: '6px',
                                        fontSize: '0.875rem',
                                        outline: 'none',
                                        transition: 'border-color 0.2s'
                                    }}
                                    onFocus={(e) => e.target.style.borderColor = 'var(--accent-primary)'}
                                    onBlur={(e) => e.target.style.borderColor = 'var(--border-primary)'}
                                />
                                {searchTerm && (
                                    <button
                                        className="btn btn-secondary"
                                        onClick={() => handleSearch('')}
                                        style={{ padding: '0.5rem 0.75rem' }}
                                    >
                                        ✕
                                    </button>
                                )}
                            </div>
                            {stockFilter && (
                                <button 
                                    className="btn btn-secondary"
                                    onClick={() => setStockFilter(null)}
                                    style={{ fontSize: '0.875rem', padding: '0.5rem 1rem' }}
                                >
                                    ✕ Clear Filter
                                </button>
                            )}
                        </div>

                        <div className="table-container">
                        <table>
                            <thead>
                                <tr>
                                <th>SKU</th>
                                <th>Product Name</th>
                                <th>Category</th>
                                <th>Current Stock</th>
                                <th>Stock Level</th>
                                <th>Avg Daily Demand</th>
                                <th>Reorder Point</th>
                                <th>Stockout Risk</th>
                                <th>Days Until Stockout</th>
                            </tr>
                        </thead>
                        <tbody>
                            {getFilteredProducts().map((product) => (
                                <tr 
                                    key={product.id}
                                    onClick={() => setSelectedProduct(product)}
                                    style={{ 
                                        cursor: 'pointer',
                                        transition: 'background-color 0.2s'
                                    }}
                                    onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f9fafb'}
                                    onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                                >
                                    <td style={{ fontFamily: 'monospace', color: 'var(--accent-primary)' }}>
                                        {product.sku}
                                    </td>
                                    <td style={{ fontWeight: 600 }}>{product.name}</td>
                                    <td>{product.category}</td>
                                    <td>
                                        <span style={{ fontSize: '1.1rem', fontWeight: 600 }}>
                                            {product.current_stock}
                                        </span>
                                    </td>
                                    <td>
                                        {(() => {
                                            const level = getStockLevelCategory(product.current_stock);
                                            return (
                                                <span style={{
                                                    padding: '0.25rem 0.5rem',
                                                    borderRadius: '3px',
                                                    backgroundColor: level.bg,
                                                    color: level.color,
                                                    fontWeight: '600',
                                                    fontSize: '0.75rem',
                                                    textTransform: 'uppercase',
                                                    letterSpacing: '0.5px'
                                                }}>
                                                    {level.label}
                                                </span>
                                            );
                                        })()}
                                    </td>
                                    <td>
                                        <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
                                            {product.average_daily_demand ? product.average_daily_demand : 'N/A'} units/day
                                        </span>
                                    </td>
                                    <td>
                                        {product.reorder_point ? (
                                            <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
                                                {product.reorder_point}
                                            </span>
                                        ) : (
                                            <span style={{ color: 'var(--text-muted)' }}>N/A</span>
                                        )}
                                    </td>
                                    <td>
                                        {(() => {
                                            const risk = product.stockout_risk;
                                            let color = '#0044ff';
                                            if (risk === 'HIGH') color = '#ff0000';
                                            else if (risk === 'MEDIUM') color = '#ff8800';
                                            return (
                                                <span style={{
                                                    padding: '0.4rem 0.8rem',
                                                    borderRadius: '4px',
                                                    backgroundColor: color + '20',
                                                    color: color,
                                                    fontWeight: 'bold',
                                                    fontSize: '0.9rem'
                                                }}>
                                                    {risk || 'UNKNOWN'}
                                                </span>
                                            );
                                        })()}
                                    </td>
                                    <td>
                                        <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
                                            {product.days_until_stockout !== null && product.days_until_stockout !== undefined
                                                ? product.days_until_stockout + ' days'
                                                : 'N/A'
                                            }
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                    </div>

                    {/* Pagination Controls */}
                    {totalPages > 1 && (
                        <div style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            marginTop: 'var(--spacing-4)',
                            padding: 'var(--spacing-4)',
                            backgroundColor: 'var(--color-gray-50)',
                            borderRadius: 'var(--border-radius-md)'
                        }}>
                            <div style={{ color: 'var(--text-secondary)' }}>
                                Showing {((currentPage - 1) * pageSize) + 1} - {Math.min(currentPage * pageSize, totalCount)} of {totalCount.toLocaleString()} products
                            </div>
                            <div style={{ display: 'flex', gap: 'var(--spacing-2)', alignItems: 'center' }}>
                                <button
                                    className="btn btn-secondary"
                                    onClick={() => setCurrentPage(1)}
                                    disabled={currentPage === 1}
                                    style={{ padding: '0.5rem 0.75rem' }}
                                >
                                    ««
                                </button>
                                <button
                                    className="btn btn-secondary"
                                    onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                                    disabled={currentPage === 1}
                                    style={{ padding: '0.5rem 0.75rem' }}
                                >
                                    « Prev
                                </button>
                                <span style={{ 
                                    padding: '0.5rem 1rem', 
                                    fontWeight: '600',
                                    backgroundColor: 'var(--accent-primary)',
                                    color: 'white',
                                    borderRadius: 'var(--border-radius-sm)'
                                }}>
                                    Page {currentPage} of {totalPages}
                                </span>
                                <button
                                    className="btn btn-secondary"
                                    onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                                    disabled={currentPage === totalPages}
                                    style={{ padding: '0.5rem 0.75rem' }}
                                >
                                    Next »
                                </button>
                                <button
                                    className="btn btn-secondary"
                                    onClick={() => setCurrentPage(totalPages)}
                                    disabled={currentPage === totalPages}
                                    style={{ padding: '0.5rem 0.75rem' }}
                                >
                                    »»
                                </button>
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* Duplicate Products Error Modal */}
            <Modal
                isOpen={duplicateError !== null}
                onClose={() => setDuplicateError(null)}
                title="⚠️ Duplicate Products Found"
                size="large"
            >
                {duplicateError && (
                    <div>
                        <p style={{ color: 'var(--color-danger)', fontWeight: '600', marginBottom: 'var(--spacing-4)' }}>
                            {duplicateError.message}
                        </p>
                        <p style={{ marginBottom: 'var(--spacing-4)', color: 'var(--text-secondary)' }}>
                            {duplicateError.suggestion}
                        </p>
                        
                        <div className="table-container">
                            <table className="table">
                                <thead>
                                    <tr>
                                        <th>SKU</th>
                                        <th>Product Name</th>
                                        <th>Current Stock in Database</th>
                                        <th>Stock in Upload File</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {duplicateError.duplicates?.map((dup, idx) => (
                                        <tr key={idx}>
                                            <td style={{ fontFamily: 'monospace', color: 'var(--color-primary)' }}>{dup.sku}</td>
                                            <td>{dup.name}</td>
                                            <td>
                                                <span style={{ fontWeight: '600', color: 'var(--color-success)' }}>
                                                    {dup.current_stock} units
                                                </span>
                                            </td>
                                            <td>
                                                <span style={{ fontWeight: '600', color: 'var(--color-warning)' }}>
                                                    {dup.file_stock} units
                                                </span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        
                        <div style={{ marginTop: 'var(--spacing-6)', padding: 'var(--spacing-4)', background: 'var(--color-gray-50)', borderRadius: 'var(--border-radius-md)' }}>
                            <h4 style={{ marginBottom: 'var(--spacing-2)', fontSize: '1rem' }}>💡 How to resolve:</h4>
                            <ul style={{ marginLeft: 'var(--spacing-5)', color: 'var(--text-secondary)' }}>
                                <li>Remove the duplicate products from your upload file and try again, OR</li>
                                <li>Use the <strong>"Restock Inventory"</strong> feature to update stock levels for existing products</li>
                            </ul>
                        </div>
                    </div>
                )}
            </Modal>

            {/* Restock Preview Modal */}
            <Modal
                isOpen={showRestockModal}
                onClose={() => {
                    setShowRestockModal(false);
                    setRestockPreview(null);
                    setSelectedRestockItems([]);
                }}
                title="📦 Restock Inventory Preview"
                size="large"
            >
                {restockPreview && (
                    <div>
                        {/* Summary Cards */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--spacing-4)', marginBottom: 'var(--spacing-6)' }}>
                            <div className="card" style={{ background: 'linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%)', border: 'none' }}>
                                <h4 style={{ color: '#7a3535', fontSize: '0.875rem', marginBottom: '4px' }}>Critical</h4>
                                <p style={{ fontSize: '2rem', fontWeight: '700', color: '#b84444' }}>
                                    {restockPreview.summary.critical}
                                </p>
                                <small style={{ color: '#7a3535' }}>Out of stock</small>
                            </div>
                            <div className="card" style={{ background: 'linear-gradient(135deg, #f5f2e8 0%, #FDE68A 100%)', border: 'none' }}>
                                <h4 style={{ color: '#92400E', fontSize: '0.875rem', marginBottom: '4px' }}>High Priority</h4>
                                <p style={{ fontSize: '2rem', fontWeight: '700', color: '#D97706' }}>
                                    {restockPreview.summary.high}
                                </p>
                                <small style={{ color: '#92400E' }}>Low stock</small>
                            </div>
                            <div className="card" style={{ background: 'linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%)', border: 'none' }}>
                                <h4 style={{ color: '#1E3A8A', fontSize: '0.875rem', marginBottom: '4px' }}>Normal</h4>
                                <p style={{ fontSize: '2rem', fontWeight: '700', color: '#2563EB' }}>
                                    {restockPreview.summary.normal}
                                </p>
                                <small style={{ color: '#1E3A8A' }}>Adequate stock</small>
                            </div>
                        </div>

                        {/* Warnings */}
                        {restockPreview.warnings && restockPreview.warnings.length > 0 && (
                            <div style={{ 
                                marginBottom: 'var(--spacing-6)', 
                                padding: 'var(--spacing-4)', 
                                background: '#f5f2e8', 
                                borderLeft: '4px solid #D97706',
                                borderRadius: 'var(--border-radius-md)'
                            }}>
                                <h4 style={{ color: '#92400E', marginBottom: 'var(--spacing-2)' }}>⚠️ Warnings:</h4>
                                <ul style={{ marginLeft: 'var(--spacing-5)', color: '#92400E' }}>
                                    {restockPreview.warnings.map((warning, idx) => (
                                        <li key={idx}>{warning}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {/* Not Found Products */}
                        {restockPreview.not_found_count > 0 && (
                            <div style={{ 
                                marginBottom: 'var(--spacing-6)', 
                                padding: 'var(--spacing-4)', 
                                background: '#FEE2E2', 
                                borderLeft: '4px solid #b84444',
                                borderRadius: 'var(--border-radius-md)'
                            }}>
                                <h4 style={{ color: '#7a3535', marginBottom: 'var(--spacing-2)' }}>
                                    ❌ {restockPreview.not_found_count} Product(s) Not Found
                                </h4>
                                <p style={{ color: '#7a3535', fontSize: '0.875rem' }}>
                                    SKUs: {restockPreview.not_found_skus.join(', ')}
                                </p>
                            </div>
                        )}

                        {/* Restock Items Table */}
                        {/* Select/Deselect All */}
                        <div style={{ marginBottom: 'var(--spacing-3)', display: 'flex', gap: 'var(--spacing-3)', alignItems: 'center' }}>
                            <button 
                                className="btn btn-secondary"
                                onClick={() => setSelectedRestockItems(restockPreview.restock_items.map(item => item.sku))}
                                style={{ fontSize: '0.875rem', padding: '0.5rem 1rem' }}
                            >
                                ✓ Select All
                            </button>
                            <button 
                                className="btn btn-secondary"
                                onClick={() => setSelectedRestockItems([])}
                                style={{ fontSize: '0.875rem', padding: '0.5rem 1rem' }}
                            >
                                ✕ Deselect All
                            </button>
                            <span style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                                {selectedRestockItems.length} of {restockPreview.restock_items.length} selected
                            </span>
                        </div>

                        <div className="table-container" style={{ maxHeight: '400px', overflowY: 'auto' }}>
                            <table className="table">
                                <thead>
                                    <tr>
                                        <th style={{ width: '40px' }}>
                                            <input
                                                type="checkbox"
                                                checked={selectedRestockItems.length === restockPreview.restock_items.length}
                                                onChange={(e) => {
                                                    if (e.target.checked) {
                                                        setSelectedRestockItems(restockPreview.restock_items.map(item => item.sku));
                                                    } else {
                                                        setSelectedRestockItems([]);
                                                    }
                                                }}
                                                style={{ cursor: 'pointer' }}
                                            />
                                        </th>
                                        <th>Priority</th>
                                        <th>SKU</th>
                                        <th>Product Name</th>
                                        <th>Current Stock</th>
                                        <th>Restock Qty</th>
                                        <th>New Stock</th>
                                        <th>Status</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {restockPreview.restock_items?.map((item, idx) => (
                                        <tr 
                                            key={idx}
                                            style={{ 
                                                opacity: selectedRestockItems.includes(item.sku) ? 1 : 0.5,
                                                backgroundColor: selectedRestockItems.includes(item.sku) ? 'transparent' : '#f9fafb'
                                            }}
                                        >
                                            <td>
                                                <input
                                                    type="checkbox"
                                                    checked={selectedRestockItems.includes(item.sku)}
                                                    onChange={(e) => {
                                                        if (e.target.checked) {
                                                            setSelectedRestockItems([...selectedRestockItems, item.sku]);
                                                        } else {
                                                            setSelectedRestockItems(selectedRestockItems.filter(sku => sku !== item.sku));
                                                        }
                                                    }}
                                                    style={{ cursor: 'pointer' }}
                                                />
                                            </td>
                                            <td>
                                                {item.priority === 'critical' && <span className="badge badge-danger">CRITICAL</span>}
                                                {item.priority === 'high' && <span className="badge badge-warning">HIGH</span>}
                                                {item.priority === 'low' && <span className="badge badge-success">NORMAL</span>}
                                            </td>
                                            <td style={{ fontFamily: 'monospace', color: 'var(--color-primary)' }}>{item.sku}</td>
                                            <td>{item.name}</td>
                                            <td>
                                                <span style={{ 
                                                    fontWeight: '600', 
                                                    color: item.current_stock === 0 ? 'var(--color-danger)' : 'var(--text-primary)' 
                                                }}>
                                                    {item.current_stock}
                                                </span>
                                            </td>
                                            <td>
                                                <span style={{ fontWeight: '600', color: 'var(--color-success)' }}>
                                                    +{item.restock_quantity}
                                                </span>
                                            </td>
                                            <td>
                                                <span style={{ fontWeight: '700', color: 'var(--color-primary)' }}>
                                                    {item.new_stock}
                                                </span>
                                            </td>
                                            <td>
                                                {item.stock_status === 'out_of_stock' && <span>🔴 Out of Stock</span>}
                                                {item.stock_status === 'low_stock' && <span>🟡 Low Stock</span>}
                                                {item.stock_status === 'high_stock' && <span>🔵 High Stock</span>}
                                                {item.stock_status === 'normal' && <span>🟢 Normal</span>}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        {/* Confirm Button */}
                        <div style={{ marginTop: 'var(--spacing-6)', display: 'flex', justifyContent: 'flex-end', gap: 'var(--spacing-3)' }}>
                            <button 
                                className="btn btn-secondary" 
                                onClick={() => {
                                    setShowRestockModal(false);
                                    setRestockPreview(null);
                                }}
                            >
                                Cancel
                            </button>
                            <button 
                                className="btn btn-primary" 
                                onClick={handleConfirmRestock}
                                disabled={selectedRestockItems.length === 0}
                                style={{ opacity: selectedRestockItems.length === 0 ? 0.5 : 1 }}
                            >
                                ✓ Confirm Restock ({selectedRestockItems.length} {selectedRestockItems.length === 1 ? 'product' : 'products'})
                            </button>
                        </div>
                    </div>
                )}
            </Modal>

            {/* Product Insights Modal */}
            <Modal
                isOpen={selectedProduct !== null}
                onClose={() => setSelectedProduct(null)}
                title={`📊 Product Insights: ${selectedProduct?.sku || ''}`}
                size="large"
            >
                {selectedProduct && (
                    <ProductInsightModal 
                        productId={selectedProduct.id} 
                        productSku={selectedProduct.sku}
                    />
                )}
            </Modal>
            
            {/* Email Alert Modal */}
            <EmailAlertModal 
                isOpen={showEmailModal}
                onClose={() => setShowEmailModal(false)}
            />

            {/* Threshold Alert Modal - Pops up when stock reaches threshold */}
            <Modal
                isOpen={showThresholdAlert}
                onClose={() => setShowThresholdAlert(false)}
                title="🚨 Stock Threshold Alert"
                size="large"
            >
                {thresholdAlerts && (
                    <div>
                        <div style={{
                            backgroundColor: '#fef2f2',
                            border: '1px solid #fecaca',
                            borderRadius: 'var(--border-radius-md)',
                            padding: 'var(--spacing-4)',
                            marginBottom: 'var(--spacing-4)'
                        }}>
                            <h3 style={{ color: '#dc2626', marginBottom: 'var(--spacing-2)' }}>
                                ⚠️ {thresholdAlerts.total_alerts} Products Need Attention
                            </h3>
                            <p style={{ color: '#7f1d1d' }}>
                                {thresholdAlerts.critical_count > 0 && (
                                    <><strong>{thresholdAlerts.critical_count}</strong> products are OUT OF STOCK. </>
                                )}
                                {thresholdAlerts.low_count > 0 && (
                                    <><strong>{thresholdAlerts.low_count}</strong> products have LOW STOCK.</>
                                )}
                            </p>
                        </div>

                        {/* Alert List */}
                        <div style={{ maxHeight: '300px', overflowY: 'auto', marginBottom: 'var(--spacing-4)' }}>
                            <table className="table" style={{ fontSize: '0.875rem' }}>
                                <thead>
                                    <tr>
                                        <th>Status</th>
                                        <th>Product</th>
                                        <th>SKU</th>
                                        <th>Stock</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {thresholdAlerts.alerts.slice(0, 20).map((alert, idx) => (
                                        <tr key={idx}>
                                            <td>
                                                <span style={{
                                                    padding: '0.25rem 0.5rem',
                                                    borderRadius: '4px',
                                                    backgroundColor: alert.alert_type === 'CRITICAL' ? '#fee2e2' : '#fef3c7',
                                                    color: alert.alert_type === 'CRITICAL' ? '#dc2626' : '#d97706',
                                                    fontWeight: 'bold',
                                                    fontSize: '0.75rem'
                                                }}>
                                                    {alert.alert_type}
                                                </span>
                                            </td>
                                            <td>{alert.name}</td>
                                            <td style={{ fontFamily: 'monospace' }}>{alert.sku}</td>
                                            <td style={{ fontWeight: 'bold', color: alert.current_stock === 0 ? '#dc2626' : '#d97706' }}>
                                                {alert.current_stock} units
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                            {thresholdAlerts.alerts.length > 20 && (
                                <p style={{ textAlign: 'center', color: 'var(--text-secondary)', marginTop: 'var(--spacing-2)' }}>
                                    ...and {thresholdAlerts.alerts.length - 20} more items
                                </p>
                            )}
                        </div>

                        {/* Send Email Section */}
                        <div style={{
                            backgroundColor: '#f0fdf4',
                            border: '1px solid #bbf7d0',
                            borderRadius: 'var(--border-radius-md)',
                            padding: 'var(--spacing-4)'
                        }}>
                            <h4 style={{ marginBottom: 'var(--spacing-3)', color: '#166534' }}>
                                📧 Send Alert Email
                            </h4>
                            <p style={{ color: '#166534', marginBottom: 'var(--spacing-3)', fontSize: '0.875rem' }}>
                                Email content is pre-filled with all alert details. Just enter the recipient's email address.
                            </p>
                            <div style={{ display: 'flex', gap: 'var(--spacing-2)' }}>
                                <input
                                    type="email"
                                    placeholder="Enter email address..."
                                    value={alertEmailTo}
                                    onChange={(e) => setAlertEmailTo(e.target.value)}
                                    style={{
                                        flex: 1,
                                        padding: '0.75rem 1rem',
                                        border: '1px solid var(--color-gray-300)',
                                        borderRadius: 'var(--border-radius-md)',
                                        fontSize: '1rem'
                                    }}
                                />
                                <button
                                    className="btn btn-primary"
                                    onClick={handleSendThresholdEmail}
                                    disabled={sendingAlert || !alertEmailTo}
                                    style={{ padding: '0.75rem 1.5rem' }}
                                >
                                    {sendingAlert ? '📤 Sending...' : '📧 Send Email'}
                                </button>
                            </div>
                        </div>

                        {/* Preview Email Content */}
                        {thresholdAlerts.alerts.length > 0 && (
                            <details style={{ marginTop: 'var(--spacing-4)' }}>
                                <summary style={{ cursor: 'pointer', color: 'var(--accent-primary)', fontWeight: '600' }}>
                                    📝 Preview Email Content
                                </summary>
                                <pre style={{
                                    backgroundColor: '#f8fafc',
                                    border: '1px solid #e2e8f0',
                                    borderRadius: 'var(--border-radius-md)',
                                    padding: 'var(--spacing-4)',
                                    marginTop: 'var(--spacing-2)',
                                    whiteSpace: 'pre-wrap',
                                    fontSize: '0.75rem',
                                    maxHeight: '200px',
                                    overflow: 'auto'
                                }}>
                                    {thresholdAlerts.alerts[0]?.email_body || 'Email content will be generated automatically.'}
                                </pre>
                            </details>
                        )}
                    </div>
                )}
            </Modal>
            </div>
        </div>
    );
};

export default Products;
