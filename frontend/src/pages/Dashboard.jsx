import React, { useState, useEffect } from 'react';
import { analyticsService, productService, emailService } from '../services/api';
import { onRefresh } from '../services/refreshService';
import { frontendCache } from '../services/cache';
import MetricCard from '../components/MetricCard';
import Modal from '../components/Modal';
import ProductsDetail from '../components/ProductsDetail';
import StockoutDetail from '../components/StockoutDetail';
import SavingsDetail from '../components/SavingsDetail';
import SalesTrendDetail from '../components/SalesTrendDetail';
import ChatbotWidget from '../components/ChatbotWidget';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, LabelList } from 'recharts';

const Dashboard = () => {
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);
    const [activeModal, setActiveModal] = useState(null);
    const [selectedPeriod, setSelectedPeriod] = useState('daily');
    const [selectedMetric, setSelectedMetric] = useState('quantity');
    const [selectedProductId, setSelectedProductId] = useState(null);
    const [products, setProducts] = useState([]);
    const [productSalesTrend, setProductSalesTrend] = useState(null);
    const [liveAlerts, setLiveAlerts] = useState([]);
    const [alertsLoading, setAlertsLoading] = useState(false);
    const [alertFilter, setAlertFilter] = useState('ALL');
    const [alertsExpanded, setAlertsExpanded] = useState(false);
    
    // Email alert state
    const [alertEmailTo, setAlertEmailTo] = useState('');
    const [sendingEmail, setSendingEmail] = useState(false);
    const [emailSent, setEmailSent] = useState(false);
    
    // Email preview state
    const [showEmailPreview, setShowEmailPreview] = useState(false);
    const [emailSubject, setEmailSubject] = useState('');
    const [emailBody, setEmailBody] = useState('');
    const [loadingPreview, setLoadingPreview] = useState(false);

    useEffect(() => {
        loadDashboard();
        loadLiveAlerts();
        loadProducts();
    }, [selectedPeriod]);

    // Listen for data refresh events from Products page (upload/restock)
    useEffect(() => {
        const cleanup = onRefresh((data) => {
            console.log('Dashboard refreshing due to:', data.source);
            loadDashboard();
            loadLiveAlerts();
        });
        return cleanup;
    }, [selectedPeriod]);
    
    // Auto-refresh when page becomes visible (user switches back to tab or window)
    useEffect(() => {
        const handleVisibilityChange = () => {
            if (!document.hidden && metrics && metrics.total_products === 0) {
                console.log('Dashboard visible with no data - auto-refreshing');
                loadDashboard();
                loadLiveAlerts();
            }
        };
        
        document.addEventListener('visibilitychange', handleVisibilityChange);
        return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
    }, [metrics]);

    useEffect(() => {
        if (selectedProductId) {
            loadProductSalesTrend();
        } else {
            setProductSalesTrend(null);
        }
    }, [selectedProductId, selectedPeriod]);

    const loadDashboard = async () => {
        try {
            setLoading(true);
            console.log('Loading dashboard with period:', selectedPeriod);
            
            // Check cache first (60 second TTL for dashboard)
            const cacheKey = `dashboard-${selectedPeriod}`;
            const cached = frontendCache.get(cacheKey, 60);
            if (cached) {
                setMetrics(cached);
                setLoading(false);
                return;
            }
            
            const response = await analyticsService.getDashboard(selectedPeriod);
            console.log('Dashboard response:', response.data);
            setMetrics(response.data);
            
            // Cache the result
            frontendCache.set(cacheKey, response.data);
            
            // Log if data appears empty
            if (response.data.total_products === 0) {
                console.warn('Dashboard returned 0 products - database may be empty or endpoint issue');
            }
        } catch (error) {
            console.error('Error loading dashboard:', error);
            console.error('Error details:', error.response?.data || error.message);
            // Show error to user
            alert('Failed to load dashboard data. Please refresh the page or check if the backend is running.');
        } finally {
            setLoading(false);
        }
    };

    const loadProducts = async () => {
        try {
            // Use the optimized dropdown endpoint (returns id, sku, name only, limited to 500)
            const response = await productService.getForDropdown('', 500);
            setProducts(response.data || []);
        } catch (error) {
            console.error('Error loading products for dropdown:', error);
        }
    };

    const loadEmailPreview = async () => {
        setLoadingPreview(true);
        try {
            const response = await emailService.getEmailPreview();
            if (response.data.has_content) {
                setEmailSubject(response.data.subject);
                setEmailBody(response.data.body);
                setShowEmailPreview(true);
            } else {
                alert('No alert items to include in email');
            }
        } catch (error) {
            console.error('Error loading email preview:', error);
            alert('Failed to load email preview');
        } finally {
            setLoadingPreview(false);
        }
    };

    // Email validation helper - supports multiple comma-separated emails
    const validateEmail = (emailString) => {
        if (!emailString || !emailString.trim()) return false;
        
        const emails = emailString.split(',').map(e => e.trim()).filter(e => e);
        const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        
        // All emails must be valid
        return emails.length > 0 && emails.every(email => emailRegex.test(email));
    };
    
    const handleSendAlertEmail = async () => {
        if (!alertEmailTo) {
            alert('Email address is required. Please enter at least one valid email address.');
            return;
        }
        
        if (!validateEmail(alertEmailTo)) {
            alert('Invalid email format. Please enter valid email addresses separated by commas.');
            return;
        }
        
        const emailCount = alertEmailTo.split(',').map(e => e.trim()).filter(e => e).length;
        
        setSendingEmail(true);
        try {
            // Send customized email content to multiple recipients
            await emailService.sendCustomEmail(alertEmailTo, emailSubject, emailBody);
            setEmailSent(true);
            setShowEmailPreview(false);
            alert(`Email sent successfully to ${emailCount} recipient${emailCount > 1 ? 's' : ''}!`);
            setTimeout(() => setEmailSent(false), 5000);
        } catch (error) {
            console.error('Email send error:', error);
            let errorMessage = 'Failed to send email';
            
            if (error.response?.data) {
                // Handle different response formats
                if (typeof error.response.data === 'string') {
                    errorMessage = error.response.data;
                } else if (error.response.data.detail) {
                    errorMessage = error.response.data.detail;
                } else if (error.response.data.message) {
                    errorMessage = error.response.data.message;
                } else {
                    // If it's an object without message/detail, stringify it
                    errorMessage = JSON.stringify(error.response.data);
                }
            } else if (error.message) {
                errorMessage = error.message;
            }
            
            alert(`Failed to send email: ${errorMessage}`);
        } finally {
            setSendingEmail(false);
        }
    };

    const loadProductSalesTrend = async () => {
        try {
            const response = await analyticsService.getProductSalesTrend(selectedProductId, selectedPeriod);
            setProductSalesTrend(response.data);
        } catch (error) {
            console.error('Error loading product sales trend:', error);
            setProductSalesTrend(null);
        }
    };

     const loadLiveAlerts = async () => {
        try {
            setAlertsLoading(true);
            
            // Check cache (45 second TTL for alerts)
            const cacheKey = 'live-alerts';
            const cached = frontendCache.get(cacheKey, 45);
            if (cached) {
                setLiveAlerts(cached.alerts || []);
                setAlertsLoading(false);
                return;
            }
            
            const response = await analyticsService.getLiveAlerts(200);
            setLiveAlerts(response.data.alerts || []);
            
            // Cache the result
            frontendCache.set(cacheKey, response.data);
        } catch (error) {
            console.error('Error loading live alerts:', error);
            setLiveAlerts([]);
        } finally {
            setAlertsLoading(false);
        }
    };

    const openModal = (modalName) => {
        setActiveModal(modalName);
    };

    const closeModal = () => {
        setActiveModal(null);
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
                        <h1 style={{ fontSize: '1.75rem', fontWeight: '700', color: 'var(--text-primary)', marginBottom: '0.25rem' }}>Dashboard Overview</h1>
                        <p style={{ color: 'var(--text-tertiary)', fontSize: '0.9rem' }}>Real-time insights into inventory performance and optimization</p>
                    </div>
                    <button 
                        className="btn btn-secondary"
                        onClick={() => {
                            loadDashboard();
                            loadLiveAlerts();
                        }}
                        style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}
                    >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>
                        Refresh
                    </button>
                </div>

                {/* Key Metrics */}
                <div className="grid grid-3 mb-4">
                    <MetricCard
                        icon="📦"
                        label="Total Products"
                        value={metrics?.total_products || 0}
                        color="primary"
                        onClick={() => openModal('products')}
                    />
                    <MetricCard
                        icon="⚠️"
                        label="Stockout Alerts"
                        value={metrics?.stockout_alerts || 0}
                        color="danger"
                        onClick={() => openModal('stockout')}
                    />
                    <MetricCard
                        icon="💰"
                        label="Est. Annual Savings"
                        value={`$${(metrics?.estimated_annual_savings || 0).toLocaleString()}`}
                        color="warning"
                        onClick={() => openModal('savings')}
                    />
                </div>
                
                {/* No Data Warning */}
                {metrics && metrics.total_products === 0 && (
                    <div style={{
                        background: '#fff3cd',
                        border: '1px solid #ffc107',
                        borderRadius: '8px',
                        padding: '1rem',
                        marginBottom: '1.5rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem'
                    }}>
                        <div style={{ fontSize: '1.5rem' }}>⚠️</div>
                        <div>
                            <strong>No data available</strong>
                            <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.875rem' }}>
                                Please go to the <strong>Products</strong> tab to upload product data and sales history, or check if the backend server is running properly.
                            </p>
                        </div>
                        <button 
                            className="btn btn-primary"
                            onClick={() => {
                                loadDashboard();
                                loadLiveAlerts();
                            }}
                            style={{ marginLeft: 'auto', whiteSpace: 'nowrap' }}
                        >
                            🔄 Retry
                        </button>
                    </div>
                )}




                {/* Modals */}
                <Modal
                    isOpen={activeModal === 'products'}
                    onClose={closeModal}
                    title="Products Overview"
                    size="large"
                >
                    <ProductsDetail />
                </Modal>

                <Modal
                    isOpen={activeModal === 'stockout'}
                    onClose={closeModal}
                    title="Stockout Alerts & At-Risk Products"
                    size="large"
                >
                    <StockoutDetail />
                </Modal>

            <Modal
                isOpen={activeModal === 'savings'}
                onClose={closeModal}
                title="💰 Estimated Annual Savings Breakdown"
                size="large"
            >
                <SavingsDetail />
            </Modal>

            <Modal
                isOpen={activeModal === 'salestrend'}
                onClose={closeModal}
                title="📈 Sales Trend & Revenue Analysis"
                size="large"
            >
                <SalesTrendDetail />
            </Modal>

            <div className="grid grid-2 mb-3">
                {/* Sales Trend Chart */}
                <div className="card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--spacing-4)' }}>
                        <div>
                            <h3 className="mb-2">Sales Trend</h3>
                            <div style={{ display: 'flex', gap: 'var(--spacing-3)', marginTop: 'var(--spacing-2)', flexWrap: 'wrap' }}>
                                {/* Time Period Selector */}
                                <select 
                                    value={selectedPeriod} 
                                    onChange={(e) => setSelectedPeriod(e.target.value)}
                                    style={{ 
                                        padding: '6px 12px',
                                        borderRadius: '6px',
                                        border: '1px solid var(--border-color)',
                                        fontSize: '0.875rem',
                                        cursor: 'pointer',
                                        backgroundColor: 'white',
                                        fontWeight: '500'
                                    }}
                                >
                                    <option value="daily">Last 30 Days (Daily)</option>
                                    <option value="wow">Week over Week (WoW)</option>
                                    <option value="mom">Month over Month (MoM)</option>
                                    <option value="yoy">Year over Year (YoY)</option>
                                </select>
                                {/* Product Selector */}
                                <select 
                                    value={selectedProductId || ''} 
                                    onChange={(e) => setSelectedProductId(e.target.value || null)}
                                    style={{ 
                                        padding: '6px 12px',
                                        borderRadius: '6px',
                                        border: '1px solid var(--border-color)',
                                        fontSize: '0.875rem',
                                        cursor: 'pointer',
                                        maxWidth: '300px'
                                    }}
                                >
                                    <option value="">All Products (Aggregate)</option>
                                    {products.map(product => (
                                    <option key={product.id} value={product.id}>
                                        {product.sku} - {product.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-2)' }}>
                        {/* Period Toggle */}
                            <div style={{ display: 'flex', gap: '4px', background: 'var(--color-gray-100)', padding: '4px', borderRadius: 'var(--border-radius-md)' }}>
                                <button 
                                    className={`btn btn-sm ${selectedPeriod === 'daily' ? 'btn-primary' : 'btn-secondary'}`}
                                    onClick={() => setSelectedPeriod('daily')}
                                    style={{ padding: '4px 12px', fontSize: '0.75rem' }}
                                    title="View daily data for the last 30 days"
                                >
                                    Daily
                                </button>
                                <button 
                                    className={`btn btn-sm ${selectedPeriod === 'wow' ? 'btn-primary' : 'btn-secondary'}`}
                                    onClick={() => setSelectedPeriod('wow')}
                                    style={{ padding: '4px 12px', fontSize: '0.75rem' }}
                                    title="Compare week over week"
                                >
                                    WoW
                                </button>
                                <button 
                                    className={`btn btn-sm ${selectedPeriod === 'mom' ? 'btn-primary' : 'btn-secondary'}`}
                                    onClick={() => setSelectedPeriod('mom')}
                                    style={{ padding: '4px 12px', fontSize: '0.75rem' }}
                                    title="Compare month over month"
                                >
                                    MoM
                                </button>
                                <button 
                                    className={`btn btn-sm ${selectedPeriod === 'yoy' ? 'btn-primary' : 'btn-secondary'}`}
                                    onClick={() => setSelectedPeriod('yoy')}
                                    style={{ padding: '4px 12px', fontSize: '0.75rem' }}
                                    title="Compare year over year"
                                >
                                    YoY
                                </button>
                            </div>
                            {/* Metric Toggle */}
                            <div style={{ display: 'flex', gap: '4px', background: 'var(--color-gray-100)', padding: '4px', borderRadius: 'var(--border-radius-md)' }}>
                                <button 
                                    className={`btn btn-sm ${selectedMetric === 'quantity' ? 'btn-primary' : 'btn-secondary'}`}
                                    onClick={() => setSelectedMetric('quantity')}
                                    style={{ padding: '4px 12px', fontSize: '0.75rem' }}
                                >
                                    Quantity
                                </button>
                                <button 
                                    className={`btn btn-sm ${selectedMetric === 'revenue' ? 'btn-primary' : 'btn-secondary'}`}
                                    onClick={() => setSelectedMetric('revenue')}
                                    style={{ padding: '4px 12px', fontSize: '0.75rem' }}
                                >
                                    Revenue
                                </button>
                                <button 
                                    className={`btn btn-sm ${selectedMetric === 'profit' ? 'btn-primary' : 'btn-secondary'}`}
                                    onClick={() => setSelectedMetric('profit')}
                                    style={{ padding: '4px 12px', fontSize: '0.75rem' }}
                                >
                                    Profit
                                </button>
                                <button 
                                    className={`btn btn-sm ${selectedMetric === 'loss' ? 'btn-primary' : 'btn-secondary'}`}
                                    onClick={() => setSelectedMetric('loss')}
                                    style={{ padding: '4px 12px', fontSize: '0.75rem' }}
                                >
                                    Loss
                                </button>
                            </div>
                        </div>
                    </div>
                    {(selectedProductId ? productSalesTrend : metrics?.sales_trend) && (selectedProductId ? productSalesTrend : metrics?.sales_trend).length > 0 ? (
                        <ResponsiveContainer width="100%" height={350}>
                            <LineChart 
                                data={selectedProductId ? productSalesTrend : metrics.sales_trend}
                                margin={{ top: 10, right: 30, left: 10, bottom: 60 }}
                            >
                                <defs>
                                    <linearGradient id="salesGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#0D9488" stopOpacity={0.8} />
                                        <stop offset="95%" stopColor="#0D9488" stopOpacity={0.1} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                                <XAxis
                                    dataKey={selectedPeriod === 'daily' ? 'date' : 'period_label'}
                                    stroke="var(--text-secondary)"
                                    style={{ fontSize: '0.75rem' }}
                                    tickFormatter={(value) => {
                                        if (selectedPeriod === 'daily') {
                                            const d = new Date(value);
                                            return `${d.getMonth() + 1}/${d.getDate()}`;
                                        }
                                        return value; // Use period_label directly (W48, Jan, 2025, etc.)
                                    }}
                                    angle={selectedPeriod === 'daily' ? 0 : -30}
                                    textAnchor={selectedPeriod === 'daily' ? 'middle' : 'end'}
                                    height={60}
                                    tick={{ dy: 10 }}
                                    interval={0}
                                    label={{ value: selectedPeriod === 'daily' ? 'Date' : selectedPeriod === 'wow' ? 'Week' : selectedPeriod === 'mom' ? 'Month' : 'Year', position: 'bottom', offset: 40, style: { fontSize: '0.75rem', fill: 'var(--text-secondary)', fontWeight: '600' } }}
                                />
                                <YAxis 
                                    stroke="var(--text-secondary)" 
                                    style={{ fontSize: '0.75rem' }}
                                    label={{ 
                                        value: selectedMetric === 'quantity' ? 'Units Sold' : selectedMetric === 'revenue' ? 'Revenue ($)' : selectedMetric === 'profit' ? 'Profit ($)' : 'Loss ($)', 
                                        angle: -90, 
                                        position: 'insideLeft', 
                                        style: { fontSize: '0.75rem', fill: 'var(--text-secondary)', fontWeight: '600', textAnchor: 'middle' } 
                                    }}
                                />
                                <Tooltip
                                    contentStyle={{
                                        background: 'rgba(255, 255, 255, 0.98)',
                                        backdropFilter: 'blur(20px)',
                                        border: '1px solid #e2e8f0',
                                        borderRadius: '8px',
                                        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
                                        padding: '12px'
                                    }}
                                    formatter={(value, name) => {
                                        if (name === 'revenue') {
                                            return [`$${value.toLocaleString()}`, 'Revenue'];
                                        } else if (name === 'quantity') {
                                            return [`${value.toLocaleString()} units`, 'Quantity'];
                                        } else if (name === 'profit') {
                                            return [`$${value.toLocaleString()}`, 'Profit'];
                                        } else if (name === 'loss') {
                                            return [`$${value.toLocaleString()}`, 'Loss'];
                                        }
                                        return [value, name];
                                    }}
                                    labelFormatter={(label) => {
                                        if (selectedPeriod === 'daily') {
                                            const d = new Date(label);
                                            if (!isNaN(d.getTime())) {
                                                return d.toLocaleDateString('en-US', { 
                                                    weekday: 'short',
                                                    year: 'numeric', 
                                                    month: 'short', 
                                                    day: 'numeric' 
                                                });
                                            }
                                        }
                                        if (selectedPeriod === 'wow') return `Week: ${label}`;
                                        if (selectedPeriod === 'mom') return `Month: ${label}`;
                                        if (selectedPeriod === 'yoy') return `Year: ${label}`;
                                        return label;
                                    }}
                                    labelStyle={{ fontWeight: '600', color: '#0f172a', marginBottom: '4px' }}
                                    cursor={{ stroke: '#0D9488', strokeWidth: 1, strokeDasharray: '5 5' }}
                                />
                                <Line
                                    type="monotone"
                                    dataKey={selectedMetric}
                                    stroke="#0D9488"
                                    strokeWidth={2.5}
                                    fill="url(#salesGradient)"
                                    dot={{ fill: '#0D9488', r: 4, strokeWidth: 2, stroke: '#fff' }}
                                    activeDot={{ r: 7, fill: '#0D9488', stroke: '#fff', strokeWidth: 3 }}
                                    connectNulls
                                >
                                    <LabelList
                                        dataKey={selectedMetric}
                                        position="top"
                                        offset={8}
                                        style={{ 
                                            fontSize: '9px', 
                                            fontWeight: '600',
                                            fill: '#475569'
                                        }}
                                        formatter={(value) => {
                                            if (value === undefined || value === null) return '';
                                            if (selectedMetric === 'revenue' || selectedMetric === 'profit' || selectedMetric === 'loss') {
                                                if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
                                                if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
                                                return `$${value}`;
                                            }
                                            if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
                                            if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
                                            return value.toLocaleString();
                                        }}
                                    />
                                </Line>
                            </LineChart>
                        </ResponsiveContainer>
                    ) : (
                        <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>
                            No sales data available
                        </p>
                    )}
                </div>

                {/* Alerts - Clean Professional Table Format */}
                <div className="card mb-3">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                        <div>
                            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}>
                                <span style={{ fontSize: '1.2rem' }}>🔔</span> Inventory Alerts
                            </h3>
                            <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>
                                Real-time inventory status and alerts
                            </p>
                        </div>
                        {liveAlerts.length > 0 && (
                            <div style={{ display: 'flex', gap: '0.5rem' }}>
                                <button 
                                    onClick={() => setAlertFilter('ALL')}
                                    style={{ 
                                        padding: '0.25rem 0.6rem', 
                                        background: alertFilter === 'ALL' ? '#4a6fa5' : '#e8f0f8', 
                                        color: alertFilter === 'ALL' ? '#fff' : '#4a6fa5', 
                                        borderRadius: '4px', 
                                        fontSize: '0.75rem', 
                                        fontWeight: '600',
                                        border: 'none',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s'
                                    }}
                                >
                                    All ({metrics?.total_products || 0})
                                </button>
                                <button 
                                    onClick={() => setAlertFilter('OUT_OF_STOCK')}
                                    style={{ 
                                        padding: '0.25rem 0.6rem', 
                                        background: alertFilter === 'OUT_OF_STOCK' ? '#b84444' : '#f0e4e4', 
                                        color: alertFilter === 'OUT_OF_STOCK' ? '#fff' : '#b84444', 
                                        borderRadius: '4px', 
                                        fontSize: '0.75rem', 
                                        fontWeight: '600',
                                        border: 'none',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s'
                                    }}
                                >
                                    {metrics?.stockout_alerts || 0} Out of Stock
                                </button>
                                <button 
                                    onClick={() => setAlertFilter('LOW')}
                                    style={{ 
                                        padding: '0.25rem 0.6rem', 
                                        background: alertFilter === 'LOW' ? '#d97706' : '#fef3c7', 
                                        color: alertFilter === 'LOW' ? '#fff' : '#d97706', 
                                        borderRadius: '4px', 
                                        fontSize: '0.75rem', 
                                        fontWeight: '600',
                                        border: 'none',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s'
                                    }}
                                >
                                    {metrics?.low_stock_count || 0} Low Stock
                                </button>
                                <button 
                                    onClick={() => setAlertFilter('MEDIUM')}
                                    style={{ 
                                        padding: '0.25rem 0.6rem', 
                                        background: alertFilter === 'MEDIUM' ? '#059669' : '#d1fae5', 
                                        color: alertFilter === 'MEDIUM' ? '#fff' : '#059669', 
                                        borderRadius: '4px', 
                                        fontSize: '0.75rem', 
                                        fontWeight: '600',
                                        border: 'none',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s'
                                    }}
                                >
                                    {metrics?.medium_stock_count || 0} Medium
                                </button>
                                <button 
                                    onClick={() => setAlertFilter('HIGH_STOCK')}
                                    style={{ 
                                        padding: '0.25rem 0.6rem', 
                                        background: alertFilter === 'HIGH_STOCK' ? '#2563eb' : '#dbeafe', 
                                        color: alertFilter === 'HIGH_STOCK' ? '#fff' : '#2563eb', 
                                        borderRadius: '4px', 
                                        fontSize: '0.75rem', 
                                        fontWeight: '600',
                                        border: 'none',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s'
                                    }}
                                >
                                    {metrics?.high_stock_count || 0} High Stock
                                </button>
                            </div>
                        )}
                    </div>
                    
                    {alertsLoading ? (
                        <p style={{ color: 'var(--text-secondary)' }}>Loading...</p>
                    ) : liveAlerts.length === 0 ? (
                        <div style={{ padding: '2rem', textAlign: 'center', background: '#f8faf8', borderRadius: '8px', border: '1px solid #d4e5d4' }}>
                            <span style={{ fontSize: '2rem' }}>✅</span>
                            <p style={{ color: '#3d6b47', marginTop: '0.5rem', fontWeight: '500' }}>All inventory levels healthy!</p>
                        </div>
                    ) : (
                        <div style={{ maxHeight: '400px', overflowY: 'auto', overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                                <thead>
                                    <tr style={{ background: '#f1f5f9', borderBottom: '2px solid #cbd5e1' }}>
                                        <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: '700', color: '#1e293b' }}>Status</th>
                                        <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: '700', color: '#1e293b' }}>Product</th>
                                        <th style={{ padding: '0.75rem 1rem', textAlign: 'center', fontWeight: '700', color: '#1e293b' }}>Stock</th>
                                        <th style={{ padding: '0.75rem 1rem', textAlign: 'center', fontWeight: '700', color: '#1e293b' }}>Days Left</th>
                                        <th style={{ padding: '0.75rem 1rem', textAlign: 'center', fontWeight: '700', color: '#1e293b' }}>Order By</th>
                                        <th style={{ padding: '0.75rem 1rem', textAlign: 'right', fontWeight: '700', color: '#1e293b' }}>Loss/Day</th>
                                        <th style={{ padding: '0.75rem 1rem', textAlign: 'left', fontWeight: '700', color: '#1e293b' }}>Action</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {(() => {
                                        const filteredAlerts = liveAlerts.filter(alert => {
                                            if (alertFilter === 'ALL') return true;
                                            if (alertFilter === 'OUT_OF_STOCK') return alert.stock_level === 'OUT_OF_STOCK';
                                            if (alertFilter === 'LOW') return alert.stock_level === 'LOW';
                                            if (alertFilter === 'MEDIUM') return alert.stock_level === 'MEDIUM';
                                            if (alertFilter === 'HIGH_STOCK') return alert.stock_level === 'HIGH';
                                            return true;
                                        });
                                        const displayAlerts = alertsExpanded ? filteredAlerts : filteredAlerts.slice(0, 5);
                                        return displayAlerts.map((alert, idx) => {
                                        const severity = (alert.severity || '').toUpperCase();
                                        const isCritical = severity === 'CRITICAL';
                                        const isHigh = severity === 'HIGH';
                                        
                                        // Status badge styling
                                        let statusLabel, statusColor, statusBg, rowBg;
                                        if (alert.type === 'STOCKOUT') {
                                            statusLabel = '🔴 OUT';
                                            statusColor = '#b84444';
                                            statusBg = '#f0e4e4';
                                            rowBg = '#fdf8f8';
                                        } else if (isCritical) {
                                            statusLabel = '🟠 CRITICAL';
                                            statusColor = '#b84444';
                                            statusBg = '#f0e4e4';
                                            rowBg = '#fdf8f8';
                                        } else if (isHigh) {
                                            statusLabel = '🟡 LOW';
                                            statusColor = '#8b6914';
                                            statusBg = '#f0ebe0';
                                            rowBg = '#fdfbf5';
                                        } else if (alert.type === 'HIGH_DEMAND') {
                                            statusLabel = '📈 TRENDING';
                                            statusColor = '#3d6b47';
                                            statusBg = '#e5f0e5';
                                            rowBg = '#f8faf8';
                                        } else {
                                            statusLabel = '⚪ WATCH';
                                            statusColor = '#5a6370';
                                            statusBg = '#e8ebee';
                                            rowBg = '#fafafa';
                                        }
                                        
                                        // Order deadline
                                        let orderDeadline = '-';
                                        if (alert.buffer_days !== undefined) {
                                            if (alert.buffer_days < 0) {
                                                orderDeadline = `${Math.abs(alert.buffer_days)}d overdue`;
                                            } else if (alert.buffer_days === 0) {
                                                orderDeadline = 'TODAY';
                                            } else {
                                                orderDeadline = `${alert.buffer_days} days`;
                                            }
                                        }
                                        
                                        return (
                                            <React.Fragment key={idx}>
                                                <tr style={{ background: rowBg, borderBottom: 'none' }}>
                                                    <td style={{ padding: '0.75rem 1rem', verticalAlign: 'top' }}>
                                                        <span style={{ 
                                                            display: 'inline-block',
                                                            padding: '0.25rem 0.5rem', 
                                                            background: statusBg, 
                                                            color: statusColor, 
                                                            borderRadius: '4px', 
                                                            fontSize: '0.7rem', 
                                                            fontWeight: '700',
                                                            whiteSpace: 'nowrap'
                                                        }}>
                                                            {statusLabel}
                                                        </span>
                                                    </td>
                                                    <td style={{ padding: '0.75rem 1rem', verticalAlign: 'top' }}>
                                                        <div style={{ fontWeight: '600', color: '#1e293b' }}>{alert.product_name}</div>
                                                        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{alert.sku} • {alert.category}</div>
                                                    </td>
                                                    <td style={{ padding: '0.75rem 1rem', textAlign: 'center', verticalAlign: 'top' }}>
                                                        <span style={{ 
                                                            fontWeight: '700', 
                                                            color: alert.type === 'STOCKOUT' ? '#b84444' : (alert.current_stock <= 50 ? '#8b6914' : '#1e293b')
                                                        }}>
                                                            {alert.type === 'STOCKOUT' ? '0' : (alert.current_stock || '-')}
                                                        </span>
                                                    </td>
                                                    <td style={{ padding: '0.75rem 1rem', textAlign: 'center', verticalAlign: 'top' }}>
                                                        <span style={{ 
                                                            fontWeight: '600', 
                                                            color: alert.type === 'STOCKOUT' ? '#b84444' : 
                                                                   (alert.days_until_stockout <= 7 ? '#b84444' : 
                                                                   alert.days_until_stockout <= 14 ? '#8b6914' : '#3d6b47')
                                                        }}>
                                                            {alert.type === 'STOCKOUT' ? '0' : (alert.days_until_stockout !== undefined ? alert.days_until_stockout : '-')}
                                                        </span>
                                                    </td>
                                                    <td style={{ padding: '0.75rem 1rem', textAlign: 'center', verticalAlign: 'top' }}>
                                                        <span style={{ 
                                                            fontWeight: '700', 
                                                            fontSize: '0.8rem',
                                                            color: alert.type === 'STOCKOUT' || (alert.buffer_days !== undefined && alert.buffer_days <= 0) ? '#b84444' : 
                                                                   (alert.buffer_days !== undefined && alert.buffer_days <= 3) ? '#8b6914' : '#3d6b47'
                                                        }}>
                                                            {alert.type === 'STOCKOUT' ? 'NOW' : orderDeadline}
                                                        </span>
                                                    </td>
                                                    <td style={{ padding: '0.75rem 1rem', textAlign: 'right', verticalAlign: 'top' }}>
                                                        {alert.loss_per_day ? (
                                                            <span style={{ fontWeight: '700', color: '#b84444' }}>
                                                                ${Math.round(alert.loss_per_day).toLocaleString()}
                                                            </span>
                                                        ) : '-'}
                                                    </td>
                                                    <td style={{ padding: '0.75rem 1rem', verticalAlign: 'top' }}>
                                                        <div style={{ fontSize: '0.8rem', color: '#3d6b47', fontWeight: '600' }}>
                                                            {alert.recommended_quantity ? (
                                                                <>Order <strong>{alert.recommended_quantity}</strong> units</>
                                                            ) : '-'}
                                                        </div>
                                                        {alert.estimated_cost && (
                                                            <div style={{ fontSize: '0.7rem', color: '#64748b' }}>
                                                                Cost: ${Math.round(alert.estimated_cost).toLocaleString()}
                                                            </div>
                                                        )}
                                                    </td>
                                                </tr>
                                                {/* Recommendation Row - NLP Style */}
                                                <tr style={{ background: rowBg, borderBottom: '1px solid #e2e8f0' }}>
                                                    <td colSpan="7" style={{ padding: '0 1rem 0.75rem 1rem' }}>
                                                        <div style={{ 
                                                            background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
                                                            borderRadius: '6px',
                                                            padding: '0.75rem 1rem',
                                                            borderLeft: `3px solid ${statusColor}`
                                                        }}>
                                                            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.5rem' }}>
                                                                <span style={{ fontSize: '1rem' }}>💡</span>
                                                                <div style={{ flex: 1 }}>
                                                                    <div style={{ fontSize: '0.7rem', color: '#64748b', marginBottom: '0.25rem', fontWeight: '600' }}>
                                                                        SUGGESTION
                                                                    </div>
                                                                    <div style={{ fontSize: '0.8rem', color: '#334155', lineHeight: '1.5' }}>
                                                                        {alert.type === 'STOCKOUT' ? (
                                                                            <>
                                                                                <strong>Immediate action required.</strong> This product is currently out of stock and customers cannot purchase it. 
                                                                                Based on the past 30 days of sales ({alert.demand_per_day || Math.round(alert.loss_per_day / 100)} units/day average), 
                                                                                you're losing approximately <strong style={{ color: '#b84444' }}>${Math.round(alert.loss_per_day).toLocaleString()}/day</strong> in potential revenue. 
                                                                                {alert.recommended_quantity && (
                                                                                    <> We recommend ordering <strong>{alert.recommended_quantity} units</strong> which covers your {alert.lead_time_days || 7}-day lead time plus a 50% safety buffer.</>
                                                                                )}
                                                                            </>
                                                                        ) : alert.buffer_days !== undefined && alert.buffer_days < 0 ? (
                                                                            <>
                                                                                <strong>Time-sensitive:</strong> Your current stock of {alert.current_stock} units will last only <strong>{alert.days_until_stockout} days</strong>, 
                                                                                but your supplier needs {alert.lead_time_days} days to deliver. 
                                                                                <span style={{ color: '#b84444' }}>Even if you order today, you'll be out of stock for {Math.abs(alert.buffer_days)} days</span>, 
                                                                                resulting in an estimated loss of <strong style={{ color: '#b84444' }}>${Math.round(Math.abs(alert.buffer_days) * alert.loss_per_day).toLocaleString()}</strong>. 
                                                                                {alert.recommended_quantity && (
                                                                                    <>Order <strong>{alert.recommended_quantity} units</strong> immediately to minimize the stockout period.</>
                                                                                )}
                                                                            </>
                                                                        ) : alert.buffer_days !== undefined && alert.buffer_days <= 3 ? (
                                                                            <>
                                                                                <strong>Order soon:</strong> You have {alert.current_stock} units remaining which will last {alert.days_until_stockout} days. 
                                                                                With a {alert.lead_time_days}-day lead time, you have <strong style={{ color: '#8b6914' }}>{alert.buffer_days} days</strong> before you need to place an order. 
                                                                                {alert.recommended_quantity && (
                                                                                    <>We suggest ordering <strong>{alert.recommended_quantity} units</strong> (${Math.round(alert.estimated_cost).toLocaleString()}) within the next {alert.buffer_days} days to maintain healthy inventory levels.</>
                                                                                )}
                                                                            </>
                                                                        ) : alert.type === 'HIGH_DEMAND' || alert.type === 'REVENUE_LOSS_PATTERN' ? (
                                                                            <>
                                                                                <strong>Opportunity detected:</strong> {alert.ai_insight || 'This product shows strong demand patterns.'}
                                                                                {alert.ai_recommendation && <> {alert.ai_recommendation}</>}
                                                                            </>
                                                                        ) : (
                                                                            <>
                                                                                <strong>Monitor:</strong> Current stock is {alert.current_stock} units with {alert.days_until_stockout} days of coverage. 
                                                                                {alert.buffer_days > 0 && <>You have {alert.buffer_days} days before needing to reorder. </>}
                                                                                {alert.ai_recommendation || 'Continue monitoring demand patterns.'}
                                                                            </>
                                                                        )}
                                                                    </div>
                                                                    {alert.consequence && (
                                                                        <div style={{ 
                                                                            marginTop: '0.5rem', 
                                                                            padding: '0.5rem', 
                                                                            background: '#fef2f2', 
                                                                            borderRadius: '4px',
                                                                            fontSize: '0.75rem',
                                                                            color: '#b84444'
                                                                        }}>
                                                                            ⚠️ <strong>Risk:</strong> {alert.consequence}
                                                                        </div>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </td>
                                                </tr>
                                            </React.Fragment>
                                        );
                                    });
                                    })()}
                                </tbody>
                            </table>
                            
                            {/* Show More / Show Less Button */}
                            {(() => {
                                const filteredAlerts = liveAlerts.filter(alert => {
                                    if (alertFilter === 'ALL') return true;
                                    if (alertFilter === 'OUT_OF_STOCK') return alert.stock_level === 'OUT_OF_STOCK';
                                    if (alertFilter === 'LOW') return alert.stock_level === 'LOW';
                                    if (alertFilter === 'MEDIUM') return alert.stock_level === 'MEDIUM';
                                    if (alertFilter === 'HIGH_STOCK') return alert.stock_level === 'HIGH';
                                    return true;
                                });
                                if (filteredAlerts.length > 5) {
                                    return (
                                        <div style={{ textAlign: 'center', marginTop: '0.75rem' }}>
                                            <button
                                                onClick={() => setAlertsExpanded(!alertsExpanded)}
                                                style={{
                                                    padding: '0.5rem 1.5rem',
                                                    background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
                                                    border: '1px solid #cbd5e1',
                                                    borderRadius: '6px',
                                                    color: '#4a6fa5',
                                                    fontSize: '0.8rem',
                                                    fontWeight: '600',
                                                    cursor: 'pointer',
                                                    transition: 'all 0.2s'
                                                }}
                                            >
                                                {alertsExpanded ? (
                                                    <>▲ Show Less</>
                                                ) : (
                                                    <>▼ Show {filteredAlerts.length - 5} More Items</>
                                                )}
                                            </button>
                                        </div>
                                    );
                                }
                                return null;
                            })()}
                        </div>
                    )}
                    
                    {/* Summary Stats */}
                    {liveAlerts.length > 0 && (() => {
                        const filteredAlerts = liveAlerts.filter(alert => {
                            if (alertFilter === 'ALL') return true;
                            if (alertFilter === 'OUT_OF_STOCK') return alert.severity === 'CRITICAL' || alert.stock_level === 'OUT';
                            if (alertFilter === 'LOW') return alert.severity === 'HIGH' || alert.stock_level === 'LOW';
                            if (alertFilter === 'MEDIUM') return alert.severity === 'MEDIUM' || alert.stock_level === 'MEDIUM';
                            if (alertFilter === 'HIGH_STOCK') return alert.severity === 'LOW' || alert.stock_level === 'HIGH';
                            return true;
                        });
                        return (
                            <div style={{ 
                                marginTop: '1rem', 
                                padding: '0.75rem 1rem', 
                                background: '#f8f9fa', 
                                borderRadius: '6px',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                fontSize: '0.8rem'
                            }}>
                                <span style={{ color: '#64748b' }}>
                                    {alertFilter !== 'ALL' ? (
                                        <>Showing <strong>{filteredAlerts.length}</strong> of {liveAlerts.length} items ({alertFilter})</>
                                    ) : (
                                        <><strong>{liveAlerts.length}</strong> items need attention</>
                                    )}
                                </span>
                                <span style={{ color: '#b84444', fontWeight: '600' }}>
                                    Total Daily Loss: ${filteredAlerts.reduce((sum, a) => sum + (a.loss_per_day || 0), 0).toLocaleString()}
                                </span>
                            </div>
                        );
                    })()}

                    {/* Email Alert Section */}
                    {liveAlerts.length > 0 && (
                        <div style={{
                            marginTop: '1rem',
                            padding: '1.25rem',
                            background: '#ffffff',
                            borderRadius: '8px',
                            border: '2px solid #4299e1',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                                <div>
                                    <h4 style={{ margin: '0 0 0.25rem 0', color: '#1a202c', fontSize: '1rem', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                        <span>📧</span> Send Alert Report
                                    </h4>
                                    <p style={{ margin: 0, color: '#4a5568', fontSize: '0.85rem' }}>
                                        Enter email addresses (comma-separated for multiple recipients)
                                    </p>
                                </div>
                            </div>
                            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', position: 'relative', marginBottom: alertEmailTo && !validateEmail(alertEmailTo) ? '20px' : '0' }}>
                                <input
                                    type="text"
                                    placeholder="email1@company.com, email2@company.com"
                                    value={alertEmailTo}
                                    onChange={(e) => setAlertEmailTo(e.target.value)}
                                    style={{
                                        flex: 1,
                                        padding: '0.7rem 0.85rem',
                                        border: `2px solid ${alertEmailTo && !validateEmail(alertEmailTo) ? '#e53e3e' : '#cbd5e0'}`,
                                        borderRadius: '6px',
                                        fontSize: '0.9rem',
                                        outline: 'none',
                                        transition: 'border-color 0.2s'
                                    }}
                                    onFocus={(e) => e.target.style.borderColor = alertEmailTo && !validateEmail(alertEmailTo) ? '#e53e3e' : '#4299e1'}
                                    onBlur={(e) => e.target.style.borderColor = alertEmailTo && !validateEmail(alertEmailTo) ? '#e53e3e' : '#cbd5e0'}
                                />
                                {alertEmailTo && !validateEmail(alertEmailTo) && (
                                    <span style={{ color: '#e53e3e', fontSize: '0.75rem', position: 'absolute', bottom: '-18px', left: 0 }}>
                                        Invalid email format (use comma-separated emails)
                                    </span>
                                )}
                                <button
                                    onClick={loadEmailPreview}
                                    disabled={loadingPreview || !alertEmailTo || !validateEmail(alertEmailTo)}
                                    style={{
                                        padding: '0.6rem 1rem',
                                        background: loadingPreview || !alertEmailTo || !validateEmail(alertEmailTo) ? '#a0aec0' : '#4a5568',
                                        color: 'white',
                                        border: 'none',
                                        borderRadius: '6px',
                                        fontSize: '0.85rem',
                                        fontWeight: '600',
                                        cursor: loadingPreview || !alertEmailTo || !validateEmail(alertEmailTo) ? 'not-allowed' : 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.4rem',
                                        whiteSpace: 'nowrap',
                                        transition: 'background 0.2s'
                                    }}
                                >
                                    {loadingPreview ? 'Loading...' : 'Preview & Send'}
                                </button>
                            </div>
                            {emailSent && (
                                <p style={{ margin: '0.5rem 0 0 0', color: '#2f855a', fontSize: '0.8rem' }}>
                                    ✓ Alert report sent successfully to {alertEmailTo}
                                </p>
                            )}
                        </div>
                    )}

                    {/* Email Preview Modal */}
                    {showEmailPreview && (
                        <div style={{
                            position: 'fixed',
                            top: 0,
                            left: 0,
                            right: 0,
                            bottom: 0,
                            background: 'rgba(0,0,0,0.5)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            zIndex: 1000
                        }}>
                            <div style={{
                                background: 'white',
                                borderRadius: '12px',
                                width: '90%',
                                maxWidth: '700px',
                                maxHeight: '85vh',
                                overflow: 'hidden',
                                boxShadow: '0 20px 60px rgba(0,0,0,0.3)'
                            }}>
                                {/* Modal Header */}
                                <div style={{
                                    background: 'linear-gradient(135deg, #3182ce 0%, #2c5282 100%)',
                                    color: 'white',
                                    padding: '1rem 1.5rem',
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center'
                                }}>
                                    <h3 style={{ margin: 0, fontSize: '1.1rem' }}>📧 Email Preview & Edit</h3>
                                    <button
                                        onClick={() => setShowEmailPreview(false)}
                                        style={{
                                            background: 'rgba(255,255,255,0.2)',
                                            border: 'none',
                                            color: 'white',
                                            width: '32px',
                                            height: '32px',
                                            borderRadius: '50%',
                                            cursor: 'pointer',
                                            fontSize: '1.2rem'
                                        }}
                                    >×</button>
                                </div>
                                
                                {/* Modal Body */}
                                <div style={{ padding: '1.5rem', maxHeight: 'calc(85vh - 140px)', overflowY: 'auto' }}>
                                    {/* To Field */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label style={{ display: 'block', fontWeight: '600', color: '#4a5568', marginBottom: '0.5rem', fontSize: '0.85rem' }}>
                                            To:
                                        </label>
                                        <input
                                            type="text"
                                            value={alertEmailTo}
                                            readOnly
                                            style={{
                                                width: '100%',
                                                padding: '0.6rem',
                                                border: '1px solid #e2e8f0',
                                                borderRadius: '6px',
                                                background: '#f7fafc',
                                                fontSize: '0.9rem'
                                            }}
                                        />
                                    </div>
                                    
                                    {/* Subject Field */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label style={{ display: 'block', fontWeight: '600', color: '#4a5568', marginBottom: '0.5rem', fontSize: '0.85rem' }}>
                                            Subject:
                                        </label>
                                        <input
                                            type="text"
                                            value={emailSubject}
                                            onChange={(e) => setEmailSubject(e.target.value)}
                                            style={{
                                                width: '100%',
                                                padding: '0.6rem',
                                                border: '2px solid #e2e8f0',
                                                borderRadius: '6px',
                                                fontSize: '0.9rem',
                                                outline: 'none'
                                            }}
                                        />
                                    </div>
                                    
                                    {/* Body Field */}
                                    <div style={{ marginBottom: '1rem' }}>
                                        <label style={{ display: 'block', fontWeight: '600', color: '#4a5568', marginBottom: '0.5rem', fontSize: '0.85rem' }}>
                                            Email Body (editable):
                                        </label>
                                        <textarea
                                            value={emailBody}
                                            onChange={(e) => setEmailBody(e.target.value)}
                                            style={{
                                                width: '100%',
                                                minHeight: '300px',
                                                padding: '0.75rem',
                                                border: '2px solid #e2e8f0',
                                                borderRadius: '6px',
                                                fontSize: '0.85rem',
                                                fontFamily: 'monospace',
                                                lineHeight: '1.5',
                                                resize: 'vertical',
                                                outline: 'none'
                                            }}
                                        />
                                    </div>
                                </div>
                                
                                {/* Modal Footer */}
                                <div style={{
                                    padding: '1rem 1.5rem',
                                    background: '#f7fafc',
                                    borderTop: '1px solid #e2e8f0',
                                    display: 'flex',
                                    justifyContent: 'flex-end',
                                    gap: '0.75rem'
                                }}>
                                    <button
                                        onClick={() => setShowEmailPreview(false)}
                                        style={{
                                            padding: '0.6rem 1.25rem',
                                            background: '#e2e8f0',
                                            color: '#4a5568',
                                            border: 'none',
                                            borderRadius: '6px',
                                            fontSize: '0.9rem',
                                            fontWeight: '600',
                                            cursor: 'pointer'
                                        }}
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleSendAlertEmail}
                                        disabled={sendingEmail}
                                        style={{
                                            padding: '0.6rem 1.5rem',
                                            background: sendingEmail ? '#a0aec0' : '#3182ce',
                                            color: 'white',
                                            border: 'none',
                                            borderRadius: '6px',
                                            fontSize: '0.9rem',
                                            fontWeight: '600',
                                            cursor: sendingEmail ? 'not-allowed' : 'pointer',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.5rem'
                                        }}
                                    >
                                        {sendingEmail ? 'Sending...' : '📤 Send Email'}
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Top Products */}
                <div className="card">
                    <h3 className="mb-2">Top Products by Revenue</h3>
                    {metrics?.top_products && metrics.top_products.length > 0 ? (
                        <ResponsiveContainer width="100%" height={300}>
                                <BarChart data={metrics.top_products} layout="vertical">
                                <defs>
                                    <linearGradient id="barGradient" x1="0" y1="0" x2="1" y2="0">
                                        <stop offset="5%" stopColor="#0D9488" stopOpacity={1} />
                                        <stop offset="95%" stopColor="#0f766e" stopOpacity={1} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                                <XAxis 
                                    type="number" 
                                    stroke="var(--text-secondary)" 
                                    style={{ fontSize: '0.75rem' }}
                                    label={{ value: 'Revenue ($)', position: 'insideBottom', offset: -5, style: { fontSize: '0.75rem', fill: 'var(--text-secondary)', fontWeight: '600' } }}
                                    tickFormatter={(value) => value >= 1000 ? `$${(value/1000).toFixed(0)}K` : `$${value}`}
                                />
                                <YAxis
                                    type="category"
                                    dataKey="name"
                                    stroke="var(--text-secondary)"
                                    style={{ fontSize: '0.75rem' }}
                                    width={120}
                                    label={{ value: 'Product', angle: -90, position: 'insideLeft', style: { fontSize: '0.75rem', fill: 'var(--text-secondary)', fontWeight: '600', textAnchor: 'middle' }, offset: 10 }}
                                />
                                <Tooltip
                                    contentStyle={{
                                        background: 'var(--glass-bg)',
                                        backdropFilter: 'blur(20px)',
                                        border: '1px solid var(--glass-border)',
                                        borderRadius: 'var(--radius-sm)',
                                    }}
                                    formatter={(value, name, props) => {
                                        if (name === 'revenue') {
                                            return [`$${value.toLocaleString()}`, `Revenue: $${value.toLocaleString()}`];
                                        }
                                        return value;
                                    }}
                                    content={({ active, payload }) => {
                                        if (active && payload && payload.length) {
                                            return (
                                                <div style={{
                                                    background: 'white',
                                                    padding: '12px',
                                                    border: '1px solid var(--border-color)',
                                                    borderRadius: 'var(--border-radius-md)',
                                                    boxShadow: 'var(--shadow-lg)'
                                                }}>
                                                    <p style={{ fontWeight: '600', marginBottom: '8px', color: 'var(--text-primary)' }}>
                                                        {payload[0].payload.name}
                                                    </p>
                                                    <p style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                                                        Quantity: {payload[0].payload.quantity.toLocaleString()} units
                                                    </p>
                                                    <p style={{ fontSize: '0.875rem', color: '#0D9488', fontWeight: '600' }}>
                                                        Revenue: ${payload[0].payload.revenue.toLocaleString()}
                                                    </p>
                                                </div>
                                            );
                                        }
                                        return null;
                                    }}
                                />
                                <Bar dataKey="revenue" fill="url(#barGradient)" radius={[0, 8, 8, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    ) : (
                        <p style={{ color: 'var(--text-secondary)', textAlign: 'center', padding: '2rem' }}>
                            No product data available
                        </p>
                    )}
                </div>

                {/* Smart recommendations for top products */}
                {metrics?.top_products && metrics.top_products.length > 0 && (
                    <div style={{ marginTop: 'var(--spacing-md)' }}>
                        <h4 className="mb-1">Recommendations</h4>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 'var(--spacing-xs)' }}>
                            Suggestions are based on demand level, margin, and recent performance of each top product.
                        </p>
                        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                            {metrics.top_products.map((p, idx) => (
                                <li key={idx} style={{ fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                                    <strong>{p.name}</strong>{' '}
                                    <span style={{ color: 'var(--text-secondary)' }}>
                                        (Demand: {p.demand_level || 'N/A'}, Profit: ${typeof p.profit === 'number' ? p.profit.toLocaleString() : 'N/A'})
                                    </span>
                                    <div style={{ marginTop: 2, color: 'var(--text-secondary)' }}>{p.ai_recommendation}</div>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}
            </div>

            {/* Smart Assistant anchored to dashboard for business users */}
            <ChatbotWidget />

            {/* Quick Actions */}
            <div className="card">
                <h3 className="mb-2">Quick Actions</h3>
                <div style={{ display: 'flex', gap: 'var(--spacing-md)', flexWrap: 'wrap' }}>
                    <button className="btn btn-primary" onClick={() => window.location.href = '/forecasting'}>
                        Generate Forecast
                    </button>
                    <button className="btn btn-secondary" onClick={() => { loadDashboard(); loadLiveAlerts(); }}>
                        Refresh Data
                    </button>
                </div>
            </div>
        </div>
    </div>
);
};

export default Dashboard;
