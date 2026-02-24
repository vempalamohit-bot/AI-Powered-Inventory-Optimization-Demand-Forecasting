import React, { useState, useEffect } from 'react';
import axios from 'axios';

const EmailSettingsTab = () => {
    const [emailConfig, setEmailConfig] = useState({
        enabled: false,
        smtp_host: 'smtp.gmail.com',
        smtp_port: 587,
        sender_email: '',
        sender_password: '',
        recipients: []
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState({ type: '', text: '' });
    const [testEmail, setTestEmail] = useState('');
    const [testing, setTesting] = useState(false);

    useEffect(() => {
        loadEmailConfig();
    }, []);

    const loadEmailConfig = async () => {
        try {
            const response = await axios.get('http://localhost:8000/api/settings/email-config');
            setEmailConfig(response.data);
        } catch (error) {
            console.error('Error loading email config:', error);
            setMessage({ type: 'error', text: 'Failed to load email configuration' });
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        setMessage({ type: '', text: '' });
        
        try {
            const response = await axios.post('http://localhost:8000/api/settings/email-config', emailConfig);
            setMessage({ type: 'success', text: response.data.message || 'Configuration saved successfully!' });
            setTimeout(() => setMessage({ type: '', text: '' }), 5000);
        } catch (error) {
            console.error('Error saving email config:', error);
            setMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to save configuration' });
        } finally {
            setSaving(false);
        }
    };

    const handleTestEmail = async () => {
        if (!testEmail) {
            setMessage({ type: 'error', text: 'Please enter a test email address' });
            return;
        }

        setTesting(true);
        setMessage({ type: '', text: '' });

        try {
            const response = await axios.post(
                'http://localhost:8000/api/alerts/send-email',
                null,
                {
                    params: {
                        email_to: testEmail,
                        subject: 'Test Email from Inventory System',
                        body: 'This is a test email to verify your SMTP configuration is working correctly.\n\nIf you received this email, your settings are configured properly!'
                    }
                }
            );
            
            if (response.data.success) {
                setMessage({ type: 'success', text: `Test email sent successfully to ${testEmail}! Check your inbox.` });
            } else {
                setMessage({ type: 'error', text: response.data.message || 'Failed to send test email' });
            }
        } catch (error) {
            console.error('Error sending test email:', error);
            setMessage({ type: 'error', text: error.response?.data?.message || 'Failed to send test email' });
        } finally {
            setTesting(false);
        }
    };

    if (loading) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <div style={{ fontSize: '1.2rem', color: '#4a5568' }}>Loading settings...</div>
            </div>
        );
    }

    return (
        <div>
            {message.text && (
                <div style={{
                    padding: '1rem',
                    marginBottom: '1.5rem',
                    borderRadius: '8px',
                    background: message.type === 'success' ? '#d4edda' : '#f8d7da',
                    color: message.type === 'success' ? '#155724' : '#721c24',
                    border: `1px solid ${message.type === 'success' ? '#c3e6cb' : '#f5c6cb'}`,
                    fontSize: '0.95rem'
                }}>
                    {message.text}
                </div>
            )}

            <div style={{
                background: '#ffffff',
                borderRadius: '12px',
                padding: '2rem',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                border: '1px solid #e2e8f0'
            }}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: '#2d3748', marginBottom: '1.5rem' }}>
                    📧 Email Configuration
                </h2>

                <div style={{ marginBottom: '2rem' }}>
                    <label style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.75rem',
                        padding: '1rem',
                        background: '#f7fafc',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        border: '2px solid #e2e8f0',
                        transition: 'all 0.2s'
                    }}>
                        <input
                            type="checkbox"
                            checked={emailConfig.enabled}
                            onChange={(e) => setEmailConfig({ ...emailConfig, enabled: e.target.checked })}
                            style={{ width: '20px', height: '20px', cursor: 'pointer' }}
                        />
                        <div>
                            <span style={{ fontSize: '1rem', fontWeight: '600', color: '#2d3748' }}>
                                Enable Email Notifications
                            </span>
                            <p style={{ fontSize: '0.85rem', color: '#718096', margin: '0.25rem 0 0 0' }}>
                                Turn this on to start receiving inventory alert emails
                            </p>
                        </div>
                    </label>
                </div>

                <div style={{ display: 'grid', gap: '1.5rem' }}>
                    <div>
                        <label style={{ display: 'block', fontWeight: '600', color: '#2d3748', marginBottom: '0.5rem', fontSize: '0.95rem' }}>
                            SMTP Host *
                        </label>
                        <input
                            type="text"
                            value={emailConfig.smtp_host}
                            onChange={(e) => setEmailConfig({ ...emailConfig, smtp_host: e.target.value })}
                            placeholder="smtp.gmail.com"
                            style={{
                                width: '100%',
                                padding: '0.75rem',
                                border: '2px solid #e2e8f0',
                                borderRadius: '6px',
                                fontSize: '0.95rem',
                                outline: 'none',
                                transition: 'border-color 0.2s'
                            }}
                            onFocus={(e) => e.target.style.borderColor = '#4299e1'}
                            onBlur={(e) => e.target.style.borderColor = '#e2e8f0'}
                        />
                        <p style={{ fontSize: '0.8rem', color: '#718096', marginTop: '0.25rem' }}>
                            Gmail: smtp.gmail.com | Outlook: smtp-mail.outlook.com
                        </p>
                    </div>

                    <div>
                        <label style={{ display: 'block', fontWeight: '600', color: '#2d3748', marginBottom: '0.5rem', fontSize: '0.95rem' }}>
                            SMTP Port *
                        </label>
                        <input
                            type="number"
                            value={emailConfig.smtp_port}
                            onChange={(e) => setEmailConfig({ ...emailConfig, smtp_port: parseInt(e.target.value) || 587 })}
                            placeholder="587"
                            style={{
                                width: '200px',
                                padding: '0.75rem',
                                border: '2px solid #e2e8f0',
                                borderRadius: '6px',
                                fontSize: '0.95rem',
                                outline: 'none',
                                transition: 'border-color 0.2s'
                            }}
                            onFocus={(e) => e.target.style.borderColor = '#4299e1'}
                            onBlur={(e) => e.target.style.borderColor = '#e2e8f0'}
                        />
                        <p style={{ fontSize: '0.8rem', color: '#718096', marginTop: '0.25rem' }}>
                            Standard port is 587 (TLS)
                        </p>
                    </div>

                    <div>
                        <label style={{ display: 'block', fontWeight: '600', color: '#2d3748', marginBottom: '0.5rem', fontSize: '0.95rem' }}>
                            Sender Email *
                        </label>
                        <input
                            type="email"
                            value={emailConfig.sender_email}
                            onChange={(e) => setEmailConfig({ ...emailConfig, sender_email: e.target.value })}
                            placeholder="your-email@gmail.com"
                            style={{
                                width: '100%',
                                padding: '0.75rem',
                                border: '2px solid #e2e8f0',
                                borderRadius: '6px',
                                fontSize: '0.95rem',
                                outline: 'none',
                                transition: 'border-color 0.2s'
                            }}
                            onFocus={(e) => e.target.style.borderColor = '#4299e1'}
                            onBlur={(e) => e.target.style.borderColor = '#e2e8f0'}
                        />
                    </div>

                    <div>
                        <label style={{ display: 'block', fontWeight: '600', color: '#2d3748', marginBottom: '0.5rem', fontSize: '0.95rem' }}>
                            Password / App Password *
                        </label>
                        <input
                            type="password"
                            value={emailConfig.sender_password === '***' ? '' : emailConfig.sender_password}
                            onChange={(e) => setEmailConfig({ ...emailConfig, sender_password: e.target.value })}
                            placeholder="Enter your app password"
                            style={{
                                width: '100%',
                                padding: '0.75rem',
                                border: '2px solid #e2e8f0',
                                borderRadius: '6px',
                                fontSize: '0.95rem',
                                outline: 'none',
                                transition: 'border-color 0.2s'
                            }}
                            onFocus={(e) => e.target.style.borderColor = '#4299e1'}
                            onBlur={(e) => e.target.style.borderColor = '#e2e8f0'}
                        />
                        <div style={{ 
                            marginTop: '0.5rem', 
                            padding: '0.75rem', 
                            background: '#fffbeb', 
                            border: '1px solid #fbbf24',
                            borderRadius: '6px'
                        }}>
                            <p style={{ fontSize: '0.85rem', color: '#92400e', margin: 0, fontWeight: '600' }}>
                                ⚠️ For Gmail: Use an App Password
                            </p>
                            <p style={{ fontSize: '0.8rem', color: '#78350f', margin: '0.25rem 0 0 0' }}>
                                Generate at <a href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener noreferrer" style={{ color: '#2563eb' }}>Google App Passwords</a>
                            </p>
                        </div>
                    </div>
                </div>

                <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem' }}>
                    <button
                        onClick={handleSave}
                        disabled={saving || !emailConfig.sender_email || !emailConfig.smtp_host}
                        style={{
                            padding: '0.75rem 2rem',
                            background: saving || !emailConfig.sender_email || !emailConfig.smtp_host ? '#cbd5e0' : '#4299e1',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            fontSize: '1rem',
                            fontWeight: '600',
                            cursor: saving || !emailConfig.sender_email || !emailConfig.smtp_host ? 'not-allowed' : 'pointer',
                            transition: 'all 0.2s',
                            boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                        }}
                    >
                        {saving ? 'Saving...' : '💾 Save Configuration'}
                    </button>
                </div>
            </div>

            {/* Test Email Section */}
            <div style={{
                background: '#ffffff',
                borderRadius: '12px',
                padding: '2rem',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                border: '1px solid #e2e8f0',
                marginTop: '2rem'
            }}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: '#2d3748', marginBottom: '1rem' }}>
                    ✉️ Test Email Configuration
                </h2>
                <p style={{ color: '#718096', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                    Send a test email to verify your SMTP settings
                </p>

                <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start' }}>
                    <div style={{ flex: 1 }}>
                        <input
                            type="email"
                            value={testEmail}
                            onChange={(e) => setTestEmail(e.target.value)}
                            placeholder="recipient@example.com"
                            style={{
                                width: '100%',
                                padding: '0.75rem',
                                border: '2px solid #e2e8f0',
                                borderRadius: '6px',
                                fontSize: '0.95rem',
                                outline: 'none'
                            }}
                        />
                    </div>
                    <button
                        onClick={handleTestEmail}
                        disabled={testing || !testEmail || !emailConfig.enabled}
                        style={{
                            padding: '0.75rem 1.5rem',
                            background: testing || !testEmail || !emailConfig.enabled ? '#cbd5e0' : '#48bb78',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            fontSize: '0.95rem',
                            fontWeight: '600',
                            cursor: testing || !testEmail || !emailConfig.enabled ? 'not-allowed' : 'pointer',
                            whiteSpace: 'nowrap'
                        }}
                    >
                        {testing ? 'Sending...' : '📤 Send Test'}
                    </button>
                </div>
                {!emailConfig.enabled && (
                    <p style={{ fontSize: '0.85rem', color: '#e53e3e', marginTop: '0.5rem' }}>
                        ⚠️ Save and enable email notifications first
                    </p>
                )}
            </div>
        </div>
    );
};

export default EmailSettingsTab;
