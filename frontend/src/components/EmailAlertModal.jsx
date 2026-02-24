import React, { useState, useEffect } from 'react';
import { emailService } from '../services/api';

const EmailAlertModal = ({ isOpen, onClose, preselectedProducts = [] }) => {
    const [step, setStep] = useState('settings'); // 'settings', 'preview', 'success'
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    
    // Email settings
    const [recipients, setRecipients] = useState('');
    const [emailConfig, setEmailConfig] = useState(null);
    
    // Alert options
    const [alertType, setAlertType] = useState('all');
    const [includeRecommendations, setIncludeRecommendations] = useState(true);
    
    // Generated email
    const [generatedEmail, setGeneratedEmail] = useState(null);
    
    useEffect(() => {
        if (isOpen) {
            loadEmailConfig();
        }
    }, [isOpen]);
    
    const loadEmailConfig = async () => {
        try {
            const response = await emailService.getConfig();
            setEmailConfig(response.data);
            setRecipients(response.data.recipients?.join(', ') || '');
        } catch (err) {
            console.error('Failed to load email config:', err);
        }
    };
    
    const handleSaveRecipients = async () => {
        try {
            setLoading(true);
            await emailService.updateConfig({ recipients: recipients });
            setError(null);
        } catch (err) {
            setError('Failed to save recipients');
        } finally {
            setLoading(false);
        }
    };
    
    const handleGenerateEmail = async () => {
        try {
            setLoading(true);
            setError(null);
            
            // Save recipients first
            await emailService.updateConfig({ recipients: recipients });
            
            // Generate email
            const response = await emailService.generateAlertEmail(
                alertType,
                preselectedProducts,
                includeRecommendations
            );
            
            setGeneratedEmail(response.data);
            setStep('preview');
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to generate email');
        } finally {
            setLoading(false);
        }
    };
    
    const handleSendEmail = async () => {
        try {
            setLoading(true);
            setError(null);
            
            const response = await emailService.sendEmail(
                generatedEmail.subject,
                generatedEmail.email_body,
                recipients.split(',').map(r => r.trim()).filter(Boolean)
            );
            
            if (response.data.mode === 'preview') {
                setError('Email sending is disabled. Configure SMTP settings to enable.');
            } else {
                setStep('success');
            }
        } catch (err) {
            console.error('Email send error:', err);
            let errorMessage = 'Failed to send email';
            
            if (err.response?.data) {
                if (typeof err.response.data === 'string') {
                    errorMessage = err.response.data;
                } else if (err.response.data.detail) {
                    errorMessage = err.response.data.detail;
                } else if (err.response.data.message) {
                    errorMessage = err.response.data.message;
                } else {
                    errorMessage = JSON.stringify(err.response.data);
                }
            } else if (err.message) {
                errorMessage = err.message;
            }
            
            setError(errorMessage);
        } finally {
            setLoading(false);
        }
    };
    
    if (!isOpen) return null;
    
    return (
        <div className="modal-overlay" onClick={onClose}>
            <div 
                className="modal-content" 
                onClick={e => e.stopPropagation()}
                style={{ maxWidth: '700px', maxHeight: '85vh', overflow: 'auto' }}
            >
                <div className="modal-header">
                    <h2>📧 Stock Alert Email Notification</h2>
                    <button className="modal-close" onClick={onClose}>×</button>
                </div>
                
                {error && (
                    <div style={{ 
                        padding: '12px', 
                        background: '#fef2f2', 
                        color: '#dc2626', 
                        borderRadius: '6px',
                        margin: '16px',
                        fontSize: '14px'
                    }}>
                        ⚠️ {error}
                    </div>
                )}
                
                {step === 'settings' && (
                    <div style={{ padding: '20px' }}>
                        <h3 style={{ marginBottom: '16px', color: '#1e293b' }}>
                            Step 1: Configure Alert Settings
                        </h3>
                        
                        {/* Recipients */}
                        <div style={{ marginBottom: '20px' }}>
                            <label style={{ 
                                display: 'block', 
                                marginBottom: '8px', 
                                fontWeight: '600',
                                color: '#334155'
                            }}>
                                📬 Recipient Email Addresses
                            </label>
                            <textarea
                                value={recipients}
                                onChange={(e) => setRecipients(e.target.value)}
                                placeholder="Enter email addresses separated by commas&#10;e.g., manager@company.com, inventory@company.com"
                                style={{
                                    width: '100%',
                                    minHeight: '80px',
                                    padding: '12px',
                                    border: '1px solid #e2e8f0',
                                    borderRadius: '8px',
                                    fontSize: '14px',
                                    resize: 'vertical'
                                }}
                            />
                            <small style={{ color: '#64748b' }}>
                                Separate multiple emails with commas
                            </small>
                        </div>
                        
                        {/* Alert Type */}
                        <div style={{ marginBottom: '20px' }}>
                            <label style={{ 
                                display: 'block', 
                                marginBottom: '8px', 
                                fontWeight: '600',
                                color: '#334155'
                            }}>
                                🎯 Alert Type
                            </label>
                            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                                {[
                                    { value: 'all', label: '🔔 All Stock Alerts', desc: 'Out of Stock + Low Stock' },
                                    { value: 'out_of_stock', label: '🔴 Out of Stock Only', desc: 'Critical items only' },
                                    { value: 'low_stock', label: '🟠 Low Stock Only', desc: 'Warning level items' }
                                ].map(option => (
                                    <div 
                                        key={option.value}
                                        onClick={() => setAlertType(option.value)}
                                        style={{
                                            flex: '1',
                                            minWidth: '180px',
                                            padding: '12px',
                                            border: alertType === option.value ? '2px solid #3b82f6' : '1px solid #e2e8f0',
                                            borderRadius: '8px',
                                            cursor: 'pointer',
                                            background: alertType === option.value ? '#eff6ff' : 'white'
                                        }}
                                    >
                                        <div style={{ fontWeight: '600', marginBottom: '4px' }}>
                                            {option.label}
                                        </div>
                                        <small style={{ color: '#64748b' }}>{option.desc}</small>
                                    </div>
                                ))}
                            </div>
                        </div>
                        
                        {/* Include Recommendations */}
                        <div style={{ marginBottom: '24px' }}>
                            <label style={{ 
                                display: 'flex', 
                                alignItems: 'center', 
                                gap: '10px',
                                cursor: 'pointer'
                            }}>
                                <input
                                    type="checkbox"
                                    checked={includeRecommendations}
                                    onChange={(e) => setIncludeRecommendations(e.target.checked)}
                                    style={{ width: '18px', height: '18px' }}
                                />
                                <span style={{ fontWeight: '500' }}>
                                    Include AI-powered recommendations in email
                                </span>
                            </label>
                        </div>
                        
                        {preselectedProducts.length > 0 && (
                            <div style={{ 
                                padding: '12px', 
                                background: '#f0fdf4', 
                                borderRadius: '8px',
                                marginBottom: '20px'
                            }}>
                                <strong>ℹ️ Note:</strong> Email will include {preselectedProducts.length} pre-selected product(s)
                            </div>
                        )}
                        
                        <button
                            onClick={handleGenerateEmail}
                            disabled={loading || !recipients.trim()}
                            className="btn btn-primary"
                            style={{
                                width: '100%',
                                padding: '14px',
                                fontSize: '16px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                gap: '8px'
                            }}
                        >
                            {loading ? '⏳ Generating...' : '✉️ Generate Email Preview'}
                        </button>
                    </div>
                )}
                
                {step === 'preview' && generatedEmail && (
                    <div style={{ padding: '20px' }}>
                        <h3 style={{ marginBottom: '16px', color: '#1e293b' }}>
                            Step 2: Review & Send
                        </h3>
                        
                        {/* Summary */}
                        <div style={{ 
                            display: 'grid', 
                            gridTemplateColumns: 'repeat(3, 1fr)', 
                            gap: '12px',
                            marginBottom: '20px'
                        }}>
                            <div style={{ padding: '12px', background: '#f8fafc', borderRadius: '8px', textAlign: 'center' }}>
                                <div style={{ fontSize: '24px', fontWeight: '700', color: '#dc2626' }}>
                                    {generatedEmail.out_of_stock_count}
                                </div>
                                <small style={{ color: '#64748b' }}>Out of Stock</small>
                            </div>
                            <div style={{ padding: '12px', background: '#f8fafc', borderRadius: '8px', textAlign: 'center' }}>
                                <div style={{ fontSize: '24px', fontWeight: '700', color: '#ea580c' }}>
                                    {generatedEmail.low_stock_count}
                                </div>
                                <small style={{ color: '#64748b' }}>Low Stock</small>
                            </div>
                            <div style={{ padding: '12px', background: '#f8fafc', borderRadius: '8px', textAlign: 'center' }}>
                                <div style={{ fontSize: '24px', fontWeight: '700', color: '#059669' }}>
                                    ${generatedEmail.estimated_reorder_cost?.toLocaleString()}
                                </div>
                                <small style={{ color: '#64748b' }}>Est. Reorder Cost</small>
                            </div>
                        </div>
                        
                        {/* Subject */}
                        <div style={{ marginBottom: '16px' }}>
                            <label style={{ fontWeight: '600', color: '#334155', display: 'block', marginBottom: '8px' }}>
                                Subject
                            </label>
                            <input
                                type="text"
                                value={generatedEmail.subject}
                                readOnly
                                style={{
                                    width: '100%',
                                    padding: '10px',
                                    border: '1px solid #e2e8f0',
                                    borderRadius: '6px',
                                    background: '#f8fafc'
                                }}
                            />
                        </div>
                        
                        {/* Recipients */}
                        <div style={{ marginBottom: '16px' }}>
                            <label style={{ fontWeight: '600', color: '#334155', display: 'block', marginBottom: '8px' }}>
                                To:
                            </label>
                            <input
                                type="text"
                                value={recipients}
                                onChange={(e) => setRecipients(e.target.value)}
                                style={{
                                    width: '100%',
                                    padding: '10px',
                                    border: '1px solid #e2e8f0',
                                    borderRadius: '6px'
                                }}
                            />
                        </div>
                        
                        {/* Email Body */}
                        <div style={{ marginBottom: '20px' }}>
                            <label style={{ fontWeight: '600', color: '#334155', display: 'block', marginBottom: '8px' }}>
                                Email Body (Auto-Generated)
                            </label>
                            <pre style={{
                                width: '100%',
                                maxHeight: '300px',
                                overflow: 'auto',
                                padding: '16px',
                                border: '1px solid #e2e8f0',
                                borderRadius: '8px',
                                background: '#f8fafc',
                                fontSize: '12px',
                                lineHeight: '1.5',
                                whiteSpace: 'pre-wrap',
                                fontFamily: 'monospace'
                            }}>
                                {generatedEmail.email_body}
                            </pre>
                        </div>
                        
                        <div style={{ display: 'flex', gap: '12px' }}>
                            <button
                                onClick={() => setStep('settings')}
                                className="btn btn-secondary"
                                style={{ flex: 1, padding: '12px' }}
                            >
                                ← Back to Settings
                            </button>
                            <button
                                onClick={handleSendEmail}
                                disabled={loading}
                                className="btn btn-primary"
                                style={{ flex: 2, padding: '12px' }}
                            >
                                {loading ? '⏳ Sending...' : '📤 Send Email Now'}
                            </button>
                        </div>
                        
                        <p style={{ marginTop: '12px', fontSize: '12px', color: '#64748b', textAlign: 'center' }}>
                            Note: Email sending requires SMTP configuration. Without it, a preview will be shown.
                        </p>
                    </div>
                )}
                
                {step === 'success' && (
                    <div style={{ padding: '40px', textAlign: 'center' }}>
                        <div style={{ fontSize: '64px', marginBottom: '16px' }}>✅</div>
                        <h3 style={{ color: '#059669', marginBottom: '12px' }}>Email Sent Successfully!</h3>
                        <p style={{ color: '#64748b', marginBottom: '24px' }}>
                            Stock alert notification has been sent to {recipients.split(',').length} recipient(s).
                        </p>
                        <button
                            onClick={onClose}
                            className="btn btn-primary"
                            style={{ padding: '12px 32px' }}
                        >
                            Close
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};

export default EmailAlertModal;
