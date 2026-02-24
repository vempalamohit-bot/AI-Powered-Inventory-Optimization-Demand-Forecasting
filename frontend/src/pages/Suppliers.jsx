import React, { useState, useEffect } from 'react';
import apiService from '../services/api';

const Suppliers = () => {
    const [suppliers, setSuppliers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showAddModal, setShowAddModal] = useState(false);
    const [selectedSupplier, setSelectedSupplier] = useState(null);
    const [formData, setFormData] = useState({
        name: '',
        country: '',
        region: '',
        contact_email: '',
        contact_phone: '',
        lead_time_days: 14,
        moq: 100
    });

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const response = await apiService.get('/suppliers');
            setSuppliers(response.data);
        } catch (error) {
            console.error('Error loading supplier data:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleAddSupplier = async (e) => {
        e.preventDefault();
        try {
            await apiService.post('/suppliers', formData);
            setShowAddModal(false);
            resetForm();
            loadData();
        } catch (error) {
            console.error('Error adding supplier:', error);
            alert('Error adding supplier');
        }
    };

    const resetForm = () => {
        setFormData({
            name: '',
            country: '',
            region: '',
            contact_email: '',
            contact_phone: '',
            lead_time_days: 14,
            moq: 100
        });
    };

    if (loading) {
        return (
            <div className="page-container">
                <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
                    <div className="spinner"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="page-container">
            <div className="container">
                {/* Page Header */}
                <div className="page-header">
                    <h1 className="page-title">Supplier Directory</h1>
                    <p className="page-subtitle">Manage your supplier contacts and information</p>
                </div>

                {/* Summary Card */}
                <div className="grid grid-1 mb-4">
                    <div className="card" style={{ padding: 'var(--spacing-4)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-3)' }}>
                            <div style={{ padding: 'var(--spacing-3)', background: 'var(--color-primary)', borderRadius: '12px' }}>
                                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2">
                                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                                    <circle cx="9" cy="7" r="4"/>
                                    <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                                    <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                                </svg>
                            </div>
                            <div>
                                <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', fontWeight: '600' }}>
                                    TOTAL SUPPLIERS
                                </div>
                                <div style={{ fontSize: '2rem', fontWeight: '700', color: 'var(--text-primary)' }}>
                                    {suppliers.length}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Suppliers Grid */}
                <div className="card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--spacing-4)' }}>
                        <h3>All Suppliers</h3>
                        <button
                            className="btn btn-primary"
                            onClick={() => setShowAddModal(true)}
                            style={{ fontSize: '14px', padding: '8px 16px' }}
                        >
                            ➕ Add Supplier
                        </button>
                    </div>

                    {suppliers.length === 0 ? (
                        <div style={{ textAlign: 'center', padding: 'var(--spacing-8)', color: 'var(--text-secondary)' }}>
                            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: '0 auto var(--spacing-4)' }}>
                                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                                <circle cx="9" cy="7" r="4"/>
                                <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                                <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                            </svg>
                            <p style={{ fontSize: '1.125rem', marginBottom: 'var(--spacing-2)' }}>No suppliers yet</p>
                            <p>Add your first supplier to start building your supplier directory</p>
                        </div>
                    ) : (
                        <div className="grid grid-3" style={{ gap: 'var(--spacing-4)' }}>
                            {suppliers.map(supplier => (
                                <div 
                                    key={supplier.id} 
                                    className="card"
                                    style={{ 
                                        padding: 'var(--spacing-5)',
                                        cursor: 'pointer',
                                        transition: 'all 0.2s'
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.boxShadow = 'var(--shadow-lg)';
                                        e.currentTarget.style.transform = 'translateY(-2px)';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.boxShadow = '';
                                        e.currentTarget.style.transform = '';
                                    }}
                                    onClick={() => setSelectedSupplier(supplier)}
                                >
                                    <h3 style={{ 
                                        fontSize: '1.125rem', 
                                        marginBottom: 'var(--spacing-3)',
                                        color: 'var(--color-primary)',
                                        fontWeight: '700'
                                    }}>
                                        {supplier.name}
                                    </h3>

                                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-2)', marginBottom: 'var(--spacing-2)' }}>
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                            <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
                                            <circle cx="12" cy="10" r="3"/>
                                        </svg>
                                        <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                                            {supplier.country}
                                        </span>
                                    </div>

                                    {supplier.contact_email && (
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-2)', marginBottom: 'var(--spacing-2)' }}>
                                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                                                <polyline points="22,6 12,13 2,6"/>
                                            </svg>
                                            <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)', wordBreak: 'break-all' }}>
                                                {supplier.contact_email}
                                            </span>
                                        </div>
                                    )}

                                    {supplier.contact_phone && (
                                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-2)', marginBottom: 'var(--spacing-3)' }}>
                                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
                                            </svg>
                                            <span style={{ fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                                                {supplier.contact_phone}
                                            </span>
                                        </div>
                                    )}

                                    <div style={{ 
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        padding: '4px 10px',
                                        background: 'var(--color-gray-100)',
                                        borderRadius: '6px',
                                        fontSize: '0.75rem',
                                        fontWeight: '600',
                                        color: 'var(--text-secondary)',
                                        marginTop: 'var(--spacing-2)'
                                    }}>
                                        ⏱️ {supplier.lead_time_days} days lead time
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Add Supplier Modal */}
                {showAddModal && (
                    <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
                        <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '600px' }}>
                            <div className="modal-header">
                                <h3>Add New Supplier</h3>
                                <button className="modal-close" onClick={() => setShowAddModal(false)}>×</button>
                            </div>
                            <form onSubmit={handleAddSupplier}>
                                <div className="modal-body">
                                    <div className="form-group">
                                        <label>Supplier Name *</label>
                                        <input
                                            type="text"
                                            value={formData.name}
                                            onChange={(e) => setFormData({...formData, name: e.target.value})}
                                            placeholder="e.g., ABC Manufacturing"
                                            required
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label>Country *</label>
                                        <input
                                            type="text"
                                            value={formData.country}
                                            onChange={(e) => setFormData({...formData, country: e.target.value})}
                                            placeholder="e.g., United States"
                                            required
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label>Region</label>
                                        <input
                                            type="text"
                                            value={formData.region}
                                            onChange={(e) => setFormData({...formData, region: e.target.value})}
                                            placeholder="e.g., North America"
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label>Contact Email</label>
                                        <input
                                            type="email"
                                            value={formData.contact_email}
                                            onChange={(e) => setFormData({...formData, contact_email: e.target.value})}
                                            placeholder="supplier@example.com"
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label>Contact Phone</label>
                                        <input
                                            type="text"
                                            value={formData.contact_phone}
                                            onChange={(e) => setFormData({...formData, contact_phone: e.target.value})}
                                            placeholder="+1-555-0123"
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label>Lead Time (days)</label>
                                        <input
                                            type="number"
                                            value={formData.lead_time_days}
                                            onChange={(e) => setFormData({...formData, lead_time_days: parseInt(e.target.value) || 0})}
                                            placeholder="14"
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label>Minimum Order Quantity (MOQ)</label>
                                        <input
                                            type="number"
                                            value={formData.moq}
                                            onChange={(e) => setFormData({...formData, moq: parseInt(e.target.value) || 0})}
                                            placeholder="100"
                                        />
                                    </div>
                                </div>
                                <div className="modal-footer">
                                    <button type="button" className="btn btn-secondary" onClick={() => { setShowAddModal(false); resetForm(); }}>
                                        Cancel
                                    </button>
                                    <button type="submit" className="btn btn-primary">
                                        Add Supplier
                                    </button>
                                </div>
                            </form>
                        </div>
                    </div>
                )}

                {/* Supplier Detail Modal */}
                {selectedSupplier && (
                    <div className="modal-overlay" onClick={() => setSelectedSupplier(null)}>
                        <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '500px' }}>
                            <div className="modal-header">
                                <h3>{selectedSupplier.name}</h3>
                                <button className="modal-close" onClick={() => setSelectedSupplier(null)}>×</button>
                            </div>
                            <div className="modal-body">
                                <div style={{ marginBottom: 'var(--spacing-4)' }}>
                                    <h4 style={{ fontSize: '0.875rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: 'var(--spacing-3)', textTransform: 'uppercase' }}>
                                        Contact Information
                                    </h4>
                                    <div style={{ display: 'grid', gap: 'var(--spacing-2)' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-3)', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                                            <span style={{ color: 'var(--text-secondary)' }}>Country:</span>
                                            <strong>{selectedSupplier.country}</strong>
                                        </div>
                                        {selectedSupplier.region && (
                                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-3)', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                                                <span style={{ color: 'var(--text-secondary)' }}>Region:</span>
                                                <strong>{selectedSupplier.region}</strong>
                                            </div>
                                        )}
                                        {selectedSupplier.contact_email && (
                                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-3)', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                                                <span style={{ color: 'var(--text-secondary)' }}>Email:</span>
                                                <a href={`mailto:${selectedSupplier.contact_email}`} style={{ color: 'var(--color-primary)', fontWeight: '600' }}>
                                                    {selectedSupplier.contact_email}
                                                </a>
                                            </div>
                                        )}
                                        {selectedSupplier.contact_phone && (
                                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-3)', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                                                <span style={{ color: 'var(--text-secondary)' }}>Phone:</span>
                                                <a href={`tel:${selectedSupplier.contact_phone}`} style={{ color: 'var(--color-primary)', fontWeight: '600' }}>
                                                    {selectedSupplier.contact_phone}
                                                </a>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                <div>
                                    <h4 style={{ fontSize: '0.875rem', fontWeight: '600', color: 'var(--text-muted)', marginBottom: 'var(--spacing-3)', textTransform: 'uppercase' }}>
                                        Business Terms
                                    </h4>
                                    <div style={{ display: 'grid', gap: 'var(--spacing-2)' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-3)', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                                            <span style={{ color: 'var(--text-secondary)' }}>Lead Time:</span>
                                            <strong>{selectedSupplier.lead_time_days} days</strong>
                                        </div>
                                        {selectedSupplier.moq && (
                                            <div style={{ display: 'flex', justifyContent: 'space-between', padding: 'var(--spacing-3)', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                                                <span style={{ color: 'var(--text-secondary)' }}>MOQ:</span>
                                                <strong>{selectedSupplier.moq} units</strong>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>
                            <div className="modal-footer">
                                <button className="btn btn-secondary" onClick={() => setSelectedSupplier(null)}>
                                    Close
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default Suppliers;
