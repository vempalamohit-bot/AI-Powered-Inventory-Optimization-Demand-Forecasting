import React from 'react';

const MetricCard = ({ icon, label, value, trend, color = 'primary', onClick }) => {
    const colorMap = {
        primary: { bg: '#f0fdfa', border: '#99f6e4', text: '#0f766e', icon: '#0D9488' },
        success: { bg: '#f0fdf4', border: '#bbf7d0', text: '#166534', icon: '#16a34a' },
        warning: { bg: '#fffbeb', border: '#fde68a', text: '#92400e', icon: '#d97706' },
        danger: { bg: '#fef2f2', border: '#fecaca', text: '#991b1b', icon: '#dc2626' },
    };

    const scheme = colorMap[color] || colorMap.primary;

    return (
        <div 
            className={`fade-in`}
            onClick={onClick}
            style={{ 
                cursor: onClick ? 'pointer' : 'default',
                padding: '1.25rem 1.5rem',
                borderRadius: '10px',
                background: '#ffffff',
                border: '1px solid #e2e8f0',
                borderLeft: `4px solid ${scheme.icon}`,
                transition: 'all 0.2s ease',
                boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
            }}
            onMouseEnter={(e) => {
                if (onClick) {
                    e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.08)';
                    e.currentTarget.style.transform = 'translateY(-1px)';
                }
            }}
            onMouseLeave={(e) => {
                if (onClick) {
                    e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.04)';
                    e.currentTarget.style.transform = 'translateY(0)';
                }
            }}
        >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                    <div style={{ fontSize: '0.8rem', fontWeight: '600', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.3px', marginBottom: '0.5rem' }}>
                        {label}
                    </div>
                    <div style={{ fontSize: '1.75rem', fontWeight: '700', color: '#0f172a', lineHeight: 1.2 }}>
                        {value}
                    </div>
                    {trend && (
                        <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.35rem' }}>
                            {trend}
                        </div>
                    )}
                </div>
                <div style={{ 
                    width: '44px', 
                    height: '44px', 
                    borderRadius: '10px', 
                    background: scheme.bg, 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                    fontSize: '1.25rem',
                    flexShrink: 0
                }}>
                    {icon}
                </div>
            </div>
            {onClick && (
                <div style={{ 
                    fontSize: '0.75rem', 
                    color: '#0D9488', 
                    marginTop: '0.75rem', 
                    fontWeight: '500',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.25rem'
                }}>
                    View details
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                        <path d="M5 12h14M12 5l7 7-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                </div>
            )}
        </div>
    );
};

export default MetricCard;