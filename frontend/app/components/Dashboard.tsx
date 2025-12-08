'use client'

import { useEffect, useState } from 'react'

const API_URL = process.env.NEXT_PUBLIC_API_URL!

interface Detection {
  id: number
  timestamp: string
  product_id: string
  product_name: string
}

interface UWBMeasurement {
  id: number
  timestamp: string
  mac_address: string
  distance_cm: number
  status: string | null
}

interface Stats {
  total_detections: number
  total_uwb_measurements: number
  latest_detection_time: string | null
  latest_uwb_time: string | null
}

export default function Dashboard() {
  const [detections, setDetections] = useState<Detection[]>([])
  const [uwbMeasurements, setUwbMeasurements] = useState<UWBMeasurement[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const fetchData = async () => {
    try {
      // Fetch latest data
      const dataRes = await fetch(`${API_URL}/data/latest?limit=20`)
      const data = await dataRes.json()
      setDetections(data.detections)
      setUwbMeasurements(data.uwb_measurements)

      // Fetch stats
      const statsRes = await fetch(`${API_URL}/stats`)
      const statsData = await statsRes.json()
      setStats(statsData)

      setLoading(false)
    } catch (err) {
      console.error('Failed to fetch data:', err)
    }
  }

  useEffect(() => {
    fetchData()

    if (autoRefresh) {
      const interval = setInterval(fetchData, 2000) // Refresh every 2 seconds
      return () => clearInterval(interval)
    }
  }, [autoRefresh])

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString()
  }

  if (loading) {
    return <div>Loading data...</div>
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Stats Overview */}
      <section style={{
        background: '#1e293b',
        padding: '1.5rem',
        borderRadius: '0.5rem',
        border: '1px solid #334155'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ margin: 0 }}>System Stats</h2>
          <button onClick={() => setAutoRefresh(!autoRefresh)}>
            {autoRefresh ? '⏸ Pause' : '▶ Resume'}
          </button>
        </div>
        
        {stats && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
            <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '0.5rem' }}>
              <div style={{ fontSize: '0.875rem', color: '#94a3b8' }}>Total Detections</div>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#3b82f6' }}>
                {stats.total_detections}
              </div>
            </div>
            <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '0.5rem' }}>
              <div style={{ fontSize: '0.875rem', color: '#94a3b8' }}>Total UWB Measurements</div>
              <div style={{ fontSize: '2rem', fontWeight: 'bold', color: '#10b981' }}>
                {stats.total_uwb_measurements}
              </div>
            </div>
            <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '0.5rem' }}>
              <div style={{ fontSize: '0.875rem', color: '#94a3b8' }}>Last Detection</div>
              <div style={{ fontSize: '1rem', fontWeight: 'bold' }}>
                {stats.latest_detection_time ? formatTime(stats.latest_detection_time) : 'None'}
              </div>
            </div>
            <div style={{ background: '#0f172a', padding: '1rem', borderRadius: '0.5rem' }}>
              <div style={{ fontSize: '0.875rem', color: '#94a3b8' }}>Last UWB</div>
              <div style={{ fontSize: '1rem', fontWeight: 'bold' }}>
                {stats.latest_uwb_time ? formatTime(stats.latest_uwb_time) : 'None'}
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Recent Detections */}
      <section style={{
        background: '#1e293b',
        padding: '1.5rem',
        borderRadius: '0.5rem',
        border: '1px solid #334155'
      }}>
        <h2>Recent Detections ({detections.length})</h2>
        
        {detections.length === 0 ? (
          <p style={{ color: '#64748b' }}>No detections yet. Waiting for RFID scans...</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #334155' }}>
                  <th style={{ textAlign: 'left', padding: '0.75rem', color: '#94a3b8' }}>Time</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem', color: '#94a3b8' }}>Product ID</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem', color: '#94a3b8' }}>Product Name</th>
                </tr>
              </thead>
              <tbody>
                {detections.map((det) => (
                  <tr key={det.id} style={{ borderBottom: '1px solid #334155' }}>
                    <td style={{ padding: '0.75rem', fontSize: '0.875rem' }}>
                      {formatTime(det.timestamp)}
                    </td>
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace', color: '#3b82f6' }}>
                      {det.product_id}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      {det.product_name}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* UWB Measurements */}
      <section style={{
        background: '#1e293b',
        padding: '1.5rem',
        borderRadius: '0.5rem',
        border: '1px solid #334155'
      }}>
        <h2>Recent UWB Measurements ({uwbMeasurements.length})</h2>
        
        {uwbMeasurements.length === 0 ? (
          <p style={{ color: '#64748b' }}>No UWB measurements yet. Waiting for anchor data...</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #334155' }}>
                  <th style={{ textAlign: 'left', padding: '0.75rem', color: '#94a3b8' }}>Time</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem', color: '#94a3b8' }}>Anchor MAC</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem', color: '#94a3b8' }}>Distance (cm)</th>
                  <th style={{ textAlign: 'left', padding: '0.75rem', color: '#94a3b8' }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {uwbMeasurements.map((uwb) => (
                  <tr key={uwb.id} style={{ borderBottom: '1px solid #334155' }}>
                    <td style={{ padding: '0.75rem', fontSize: '0.875rem' }}>
                      {formatTime(uwb.timestamp)}
                    </td>
                    <td style={{ padding: '0.75rem', fontFamily: 'monospace', color: '#10b981' }}>
                      {uwb.mac_address}
                    </td>
                    <td style={{ padding: '0.75rem', fontWeight: 'bold' }}>
                      {uwb.distance_cm.toFixed(1)} cm
                    </td>
                    <td style={{ padding: '0.75rem', fontSize: '0.875rem', color: '#64748b' }}>
                      {uwb.status || 'N/A'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
