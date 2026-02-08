import { useState, useEffect } from 'react'
import { api } from '../api/client'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import './Telemetry.css'

function Telemetry({ jobId }) {
    const [telemetryData, setTelemetryData] = useState([])
    const [currentData, setCurrentData] = useState(null)

    useEffect(() => {
        const interval = setInterval(async () => {
            try {
                const data = await api.getJobTelemetry(jobId)
                setCurrentData(data)

                // Add to history (keep last 30 data points)
                setTelemetryData(prev => {
                    const newData = [
                        ...prev,
                        {
                            time: new Date().toLocaleTimeString(),
                            cpu: data.cpu_usage,
                            ram: data.ram_usage_mb,
                        }
                    ]
                    return newData.slice(-30)
                })
            } catch (err) {
                console.error('Failed to fetch telemetry:', err)
            }
        }, 2000)

        return () => clearInterval(interval)
    }, [jobId])

    return (
        <div className="telemetry-container card">
            <h3>📊 System Telemetry</h3>

            {currentData && (
                <div className="telemetry-stats">
                    <div className="stat-card">
                        <span className="stat-label">CPU Usage</span>
                        <span className="stat-value">{currentData.cpu_usage.toFixed(1)}%</span>
                    </div>
                    <div className="stat-card">
                        <span className="stat-label">RAM Usage</span>
                        <span className="stat-value">{currentData.ram_usage_mb.toFixed(0)} MB</span>
                    </div>
                    {currentData.current_tool && (
                        <div className="stat-card wide">
                            <span className="stat-label">Current Tool</span>
                            <span className="stat-value small">{currentData.current_tool}</span>
                        </div>
                    )}
                </div>
            )}

            {telemetryData.length > 0 && (
                <div className="telemetry-chart">
                    <ResponsiveContainer width="100%" height={250}>
                        <LineChart data={telemetryData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
                            <XAxis dataKey="time" stroke="#9ca3af" />
                            <YAxis stroke="#9ca3af" />
                            <Tooltip
                                contentStyle={{
                                    background: '#1a2332',
                                    border: '1px solid #2d3748',
                                    borderRadius: '0.5rem',
                                }}
                            />
                            <Legend />
                            <Line type="monotone" dataKey="cpu" stroke="#3b82f6" name="CPU %" />
                            <Line type="monotone" dataKey="ram" stroke="#10b981" name="RAM (MB)" />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
    )
}

export default Telemetry
