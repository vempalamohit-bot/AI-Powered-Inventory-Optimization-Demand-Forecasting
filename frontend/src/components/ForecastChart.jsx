import React, { useMemo } from 'react';
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    LabelList,
} from 'recharts';

/**
 * Aggregate daily data into weekly buckets for cleaner visualization.
 */
function aggregateWeekly(data) {
    const weeks = {};
    data.forEach(d => {
        const date = new Date(d.date);
        const day = date.getDay();
        const diff = date.getDate() - day + (day === 0 ? -6 : 1);
        const monday = new Date(date.setDate(diff));
        const weekKey = monday.toISOString().slice(0, 10);
        
        if (!weeks[weekKey]) {
            weeks[weekKey] = { date: weekKey, actual: 0, predicted: 0, hasActual: false, hasPredicted: false, dayCount: 0 };
        }
        if (d.actual !== undefined && d.actual !== null) {
            weeks[weekKey].actual += d.actual;
            weeks[weekKey].hasActual = true;
        }
        if (d.predicted !== undefined && d.predicted !== null) {
            weeks[weekKey].predicted += d.predicted;
            weeks[weekKey].hasPredicted = true;
        }
        weeks[weekKey].dayCount++;
    });
    
    return Object.values(weeks)
        .sort((a, b) => a.date.localeCompare(b.date))
        .map(w => ({
            date: w.date,
            ...(w.hasActual ? { actual: Math.round(w.actual) } : {}),
            ...(w.hasPredicted ? { predicted: Math.round(w.predicted) } : {}),
        }));
}

const ForecastChart = ({ data }) => {
    const chartData = useMemo(() => {
        const historicalPoints = data.filter(d => d.actual !== undefined && d.predicted === undefined);
        const forecastPoints = data.filter(d => d.predicted !== undefined);
        
        // Trim historical to last 28 days for weekly aggregation clarity
        const trimmedHist = historicalPoints.slice(-28);
        const trimmedData = [...trimmedHist, ...forecastPoints];
        
        const source = aggregateWeekly(trimmedData);
        return source.map((d, i) => ({
            ...d,
            predictedLabel: (i % 1 === 0 || i === source.length - 1) && d.predicted !== undefined 
                ? Math.round(d.predicted) 
                : null,
            actualLabel: (i % 1 === 0 || i === source.length - 1) && d.actual !== undefined 
                ? Math.round(d.actual) 
                : null,
        }));
    }, [data]);

    const CustomTooltip = ({ active, payload, label }) => {
        if (active && payload && payload.length) {
            return (
                <div style={{
                    background: '#ffffff',
                    border: '1px solid #e2e8f0',
                    borderRadius: '8px',
                    padding: '0.75rem 1rem',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
                    fontSize: '0.8rem',
                }}>
                    <p style={{ color: '#1e293b', marginBottom: '0.4rem', fontWeight: '600', fontSize: '0.8rem' }}>
                        {label}
                    </p>
                    {payload.map((entry, index) => (
                        <p key={index} style={{ color: entry.color, fontSize: '0.8rem', margin: '0.2rem 0', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: entry.color, display: 'inline-block' }}></span>
                            {entry.name}: <strong>{Math.round(entry.value)}</strong>
                        </p>
                    ))}
                </div>
            );
        }
        return null;
    };

    return (
        <div>
            <ResponsiveContainer width="100%" height={420}>
                <AreaChart data={chartData} margin={{ top: 20, right: 30, left: 10, bottom: 10 }}>
                    <defs>
                        <linearGradient id="colorPredicted" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#0D9488" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#0D9488" stopOpacity={0.02} />
                        </linearGradient>
                        <linearGradient id="colorActual" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.25} />
                            <stop offset="95%" stopColor="#6366f1" stopOpacity={0.02} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
                    <XAxis
                        dataKey="date"
                        stroke="#94a3b8"
                        style={{ fontSize: '0.7rem' }}
                        tickLine={false}
                        axisLine={{ stroke: '#e2e8f0' }}
                        label={{ value: 'Date', position: 'insideBottom', offset: -5, style: { fontSize: '0.75rem', fill: '#94a3b8', fontWeight: '500' } }}
                    />
                    <YAxis 
                        stroke="#94a3b8" 
                        style={{ fontSize: '0.7rem' }}
                        tickLine={false}
                        axisLine={false}
                        label={{ value: 'Units', angle: -90, position: 'insideLeft', style: { fontSize: '0.75rem', fill: '#94a3b8', fontWeight: '500', textAnchor: 'middle' } }}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                        wrapperStyle={{ color: '#475569', fontSize: '0.8rem', paddingTop: '0.5rem' }}
                        iconType="circle"
                        iconSize={8}
                    />

                    {chartData.some(d => d.actual !== undefined) && (
                        <Area
                            type="monotone"
                            dataKey="actual"
                            stroke="#6366f1"
                            strokeWidth={2.5}
                            fill="url(#colorActual)"
                            name="Actual Demand"
                        >
                            <LabelList
                                dataKey="actualLabel"
                                position="bottom"
                                fill="#6366f1"
                                fontSize={10}
                                fontWeight={700}
                                offset={10}
                            />
                        </Area>
                    )}

                    <Area
                        type="monotone"
                        dataKey="predicted"
                        stroke="#0D9488"
                        strokeWidth={2.5}
                        fill="url(#colorPredicted)"
                        name="Predicted Demand"
                        strokeDasharray="6 3"
                    >
                        <LabelList
                            dataKey="predictedLabel"
                            position="top"
                            fill="#0D9488"
                            fontSize={10}
                            fontWeight={700}
                            offset={10}
                        />
                    </Area>
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
};

export default ForecastChart;
