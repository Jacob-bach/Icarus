import { useState, useEffect, useRef } from 'react'
import { api } from '../api/client'
import './Terminal.css'

function Terminal({ jobId }) {
    const [logs, setLogs] = useState([])
    const [connected, setConnected] = useState(false)
    const logsEndRef = useRef(null)
    const wsRef = useRef(null)

    useEffect(() => {
        // Try to connect WebSocket for live streaming
        try {
            const ws = api.createWebSocket(jobId)
            wsRef.current = ws

            ws.onopen = () => {
                setConnected(true)
                addLog('info', 'Connected to job stream')
            }

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data)
                if (data.type === 'status_update') {
                    addLog('status', `Status: ${data.status}`)
                } else if (data.type === 'log') {
                    addLog('log', data.message)
                }
            }

            ws.onerror = () => {
                addLog('error', 'WebSocket connection error')
                setConnected(false)
            }

            ws.onclose = () => {
                addLog('info', 'Disconnected from job stream')
                setConnected(false)
            }

            return () => {
                if (ws) ws.close()
            }
        } catch (err) {
            console.error('Failed to create WebSocket:', err)
        }
    }, [jobId])

    const addLog = (type, message) => {
        setLogs(prev => [...prev, {
            timestamp: new Date().toLocaleTimeString(),
            type,
            message,
        }])
    }

    useEffect(() => {
        logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [logs])

    return (
        <div className="terminal-container card">
            <div className="terminal-header">
                <h3>💻 Live Terminal</h3>
                <span className={`connection-status ${connected ? 'connected' : 'disconnected'}`}>
                    {connected ? '● Connected' : '○ Disconnected'}
                </span>
            </div>

            <div className="terminal-output">
                {logs.length === 0 ? (
                    <div className="terminal-empty">Waiting for log output...</div>
                ) : (
                    logs.map((log, idx) => (
                        <div key={idx} className={`terminal-line ${log.type}`}>
                            <span className="terminal-timestamp">[{log.timestamp}]</span>
                            <span className="terminal-message">{log.message}</span>
                        </div>
                    ))
                )}
                <div ref={logsEndRef} />
            </div>
        </div>
    )
}

export default Terminal
