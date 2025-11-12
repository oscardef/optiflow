'use client'

import { useEffect, useState } from 'react'
import Dashboard from './components/Dashboard'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function Home() {
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Check backend connectivity
    fetch(`${API_URL}/`)
      .then(res => res.json())
      .then(() => setConnected(true))
      .catch(err => {
        setError(err.message)
        setConnected(false)
      })
  }, [])

  return (
    <main>
      <div style={{ marginBottom: '2rem' }}>
        <h1>OptiFlow Dashboard</h1>
        <p style={{ color: '#94a3b8' }}>
          Real-time inventory tracking with RFID and UWB positioning
        </p>
        <div style={{ marginTop: '0.5rem' }}>
          <span style={{
            display: 'inline-block',
            padding: '0.25rem 0.75rem',
            borderRadius: '0.25rem',
            fontSize: '0.875rem',
            background: connected ? '#10b981' : '#ef4444',
            color: 'white'
          }}>
            {connected ? '● Connected' : '● Disconnected'}
          </span>
          {error && (
            <span style={{ marginLeft: '1rem', color: '#ef4444', fontSize: '0.875rem' }}>
              {error}
            </span>
          )}
        </div>
      </div>

      {connected ? (
        <Dashboard />
      ) : (
        <div style={{
          padding: '2rem',
          background: '#1e293b',
          borderRadius: '0.5rem',
          textAlign: 'center'
        }}>
          <p>Waiting for backend connection...</p>
          <p style={{ fontSize: '0.875rem', color: '#64748b', marginTop: '0.5rem' }}>
            Make sure the backend is running at {API_URL}
          </p>
        </div>
      )}
    </main>
  )
}
