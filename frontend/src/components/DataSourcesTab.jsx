import React from 'react';
import ApiIntegration from '../pages/ApiIntegration';

const DataSourcesTab = () => {
    return (
        <div>
            {/* Admin Banner */}
            <div style={{
                background: 'linear-gradient(135deg, #FFC107 0%, #FF9800 100%)',
                borderRadius: '12px',
                padding: '1rem 1.5rem',
                marginBottom: '1.5rem',
                color: '#000',
                display: 'flex',
                alignItems: 'center',
                gap: '1rem'
            }}>
                <span style={{ fontSize: '2rem' }}>⚠️</span>
                <div>
                    <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>Admin/Developer Section</div>
                    <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>
                        This section is for API data ingestion and system configuration. 
                        <strong> Business users should use the "Upload Data" feature in the Products page.</strong>
                    </div>
                </div>
            </div>

            {/* Integration Info */}
            <div style={{
                background: '#e3f2fd',
                borderRadius: '8px',
                padding: '1rem',
                marginBottom: '1.5rem',
                border: '1px solid #90caf9'
            }}>
                <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: '#1565c0' }}>
                    🔄 How Data Sources Work:
                </div>
                <ul style={{ margin: '0.5rem 0 0 1.5rem', color: '#0d47a1', fontSize: '0.9rem', lineHeight: '1.6' }}>
                    <li>CSV Upload (Products page) → Schema validated → JSON generated → AI models triggered</li>
                    <li>API Integration → Data fetched → Columns mapped → Database updated</li>
                    <li>Generated data includes extra fields: supplier, warehouse, brand, etc.</li>
                    <li>All processes run automatically in the background</li>
                </ul>
            </div>

            {/* API Integration Component */}
            <ApiIntegration />
        </div>
    );
};

export default DataSourcesTab;
