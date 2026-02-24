import React, { useState } from 'react';
import EmailSettingsTab from '../components/EmailSettingsTab';
import DataSourcesTab from '../components/DataSourcesTab';

const Settings = () => {
    const [activeTab, setActiveTab] = useState('email');

    const tabs = [
        { id: 'email', name: 'Email & Notifications', icon: '📧' },
        { id: 'data-sources', name: 'Data Sources (Admin)', icon: '🔌', admin: true }
    ];

    return (
        <div className="container" style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
            {/* Header */}
            <div style={{ marginBottom: '2rem' }}>
                <h1 style={{ fontSize: '2rem', fontWeight: '700', color: '#1a202c', marginBottom: '0.5rem' }}>
                    ⚙️ Settings & Configuration
                </h1>
                <p style={{ color: '#4a5568', fontSize: '1rem' }}>
                    Manage system configuration, data sources, and notifications
                </p>
            </div>

            {/* Tab Navigation */}
            <div style={{
                display: 'flex',
                gap: '0.5rem',
                borderBottom: '2px solid #e2e8f0',
                marginBottom: '2rem',
                overflowX: 'auto'
            }}>
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        style={{
                            padding: '0.75rem 1.5rem',
                            border: 'none',
                            background: 'transparent',
                            borderBottom: activeTab === tab.id ? '3px solid #0F62FE' : '3px solid transparent',
                            color: activeTab === tab.id ? '#0F62FE' : '#4a5568',
                            fontWeight: activeTab === tab.id ? '600' : '400',
                            fontSize: '0.95rem',
                            cursor: 'pointer',
                            transition: 'all 0.2s',
                            whiteSpace: 'nowrap',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                        }}
                    >
                        <span>{tab.icon}</span>
                        <span>{tab.name}</span>
                        {tab.admin && (
                            <span style={{
                                fontSize: '0.7rem',
                                background: '#FFC107',
                                color: '#000',
                                padding: '0.15rem 0.4rem',
                                borderRadius: '4px',
                                fontWeight: '600'
                            }}>
                                ADMIN
                            </span>
                        )}
                    </button>
                ))}
            </div>

            {/* Tab Content */}
            <div>
                {activeTab === 'email' && <EmailSettingsTab />}
                {activeTab === 'data-sources' && <DataSourcesTab />}
            </div>
        </div>
    );
};

export default Settings;
