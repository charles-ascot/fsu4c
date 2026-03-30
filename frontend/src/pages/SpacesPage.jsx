import { useEffect, useState } from 'react'
import { api } from '../api'
import LoadingSpinner from '../components/LoadingSpinner'

export default function SpacesPage() {
  const [spaces, setSpaces] = useState([])
  const [loading, setLoading] = useState(true)
  const [discovering, setDiscovering] = useState(false)
  const [discovered, setDiscovered] = useState([])
  const [registeringId, setRegisteringId] = useState(null)
  const [error, setError] = useState(null)

  const load = () => {
    setLoading(true)
    api.getSpaces()
      .then(r => setSpaces(r.data?.spaces ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleDiscover = () => {
    setDiscovering(true)
    api.discoverSpaces()
      .then(r => setDiscovered(r.data?.available_spaces ?? []))
      .catch(e => setError(e.message))
      .finally(() => setDiscovering(false))
  }

  const handleRegister = (space) => {
    setRegisteringId(space.space_resource_name)
    api.registerSpace({ space_resource_name: space.space_resource_name })
      .then(() => { load(); setDiscovered(d => d.filter(s => s.space_resource_name !== space.space_resource_name)) })
      .catch(e => setError(e.message))
      .finally(() => setRegisteringId(null))
  }

  const handleDelete = (spaceId) => {
    if (!confirm('Remove this space from monitoring?')) return
    api.deleteSpace(spaceId).then(load).catch(e => setError(e.message))
  }

  if (loading) return <div className="flex justify-center pt-20"><LoadingSpinner size={8} /></div>

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="gradient-text text-2xl font-bold">Spaces</h1>
          <p className="text-xs mt-0.5" style={{ color: 'var(--text-dim)' }}>Registered Chat spaces being monitored</p>
        </div>
        <button
          onClick={handleDiscover}
          disabled={discovering}
          className="px-4 py-2 rounded-lg text-sm font-medium transition-opacity hover:opacity-80 disabled:opacity-40"
          style={{ background: 'rgba(0,212,255,0.15)', border: '1px solid rgba(0,212,255,0.3)', color: 'var(--cyan)' }}
        >
          {discovering ? 'Discovering…' : 'Discover Spaces'}
        </button>
      </div>

      {error && (
        <div className="glass-panel p-4 mb-4 text-sm" style={{ color: 'var(--red)' }}>{error}</div>
      )}

      {/* Discovered (unregistered) spaces */}
      {discovered.length > 0 && (
        <div className="glass-panel overflow-hidden mb-6">
          <div className="px-5 py-3 col-header" style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
            Available to Register ({discovered.filter(s => !s.already_registered).length})
          </div>
          {discovered.filter(s => !s.already_registered).map(space => (
            <div key={space.space_resource_name}
              className="flex items-center gap-4 px-5 py-3"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <div className="flex-1 min-w-0">
                <div className="text-sm" style={{ color: 'var(--text)' }}>{space.display_name || space.space_resource_name}</div>
                <div className="text-xs mt-0.5" style={{ color: 'var(--text-dim)' }}>{space.space_resource_name} · {space.space_type}</div>
              </div>
              <button
                onClick={() => handleRegister(space)}
                disabled={registeringId === space.space_resource_name}
                className="px-3 py-1 rounded text-xs font-medium transition-opacity hover:opacity-80 disabled:opacity-40"
                style={{ background: 'rgba(74,222,128,0.15)', border: '1px solid rgba(74,222,128,0.3)', color: '#4ade80' }}
              >
                {registeringId === space.space_resource_name ? '…' : 'Register'}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Registered spaces */}
      <div className="glass-panel overflow-hidden">
        <div className="px-5 py-3 col-header" style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
          Monitoring ({spaces.length})
        </div>
        {spaces.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm" style={{ color: 'var(--text-dim)' }}>
            No spaces registered. Click "Discover Spaces" to find available spaces.
          </div>
        ) : spaces.map(space => (
          <div key={space.space_id}
            className="flex items-center gap-4 px-5 py-3"
            style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
            <div className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ background: space.active ? 'var(--green)' : 'var(--text-dim)' }} />
            <div className="flex-1 min-w-0">
              <div className="text-sm" style={{ color: 'var(--text)' }}>{space.display_name}</div>
              <div className="text-xs mt-0.5" style={{ color: 'var(--text-dim)' }}>
                {space.space_resource_name} · {space.space_type} · {space.message_count ?? 0} messages
              </div>
            </div>
            <button
              onClick={() => handleDelete(space.space_id)}
              className="text-xs transition-opacity hover:opacity-80"
              style={{ color: 'var(--red)' }}
            >
              Remove
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
