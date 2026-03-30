import { useEffect, useState } from 'react'
import { api } from '../api'
import LoadingSpinner from '../components/LoadingSpinner'

export default function ApiKeysPage() {
  const [keys, setKeys] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [newKeyResult, setNewKeyResult] = useState(null)
  const [form, setForm] = useState({ service_name: '', description: '' })
  const [error, setError] = useState(null)

  const load = () => {
    setLoading(true)
    api.getApiKeys()
      .then(r => setKeys(r.data?.keys ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleCreate = () => {
    if (!form.service_name.trim()) return
    setCreating(true)
    api.createApiKey(form)
      .then(r => { setNewKeyResult(r.data); load(); setForm({ service_name: '', description: '' }) })
      .catch(e => setError(e.message))
      .finally(() => setCreating(false))
  }

  const handleRevoke = (keyId) => {
    if (!confirm('Revoke this key? It will become immediately invalid.')) return
    api.revokeApiKey(keyId).then(load).catch(e => setError(e.message))
  }

  if (loading) return <div className="flex justify-center pt-20"><LoadingSpinner size={8} /></div>

  return (
    <div className="max-w-3xl">
      <div className="mb-6">
        <h1 className="gradient-text text-2xl font-bold">API Keys</h1>
        <p className="text-xs mt-0.5" style={{ color: 'var(--text-dim)' }}>
          Service keys for inter-FSU and AI conductor access
        </p>
      </div>

      {error && <div className="glass-panel p-4 mb-4 text-sm" style={{ color: 'var(--red)' }}>{error}</div>}

      {/* New key result — shown once */}
      {newKeyResult && (
        <div className="glass-panel p-5 mb-6" style={{ border: '1px solid rgba(74,222,128,0.3)' }}>
          <div className="flex items-center justify-between mb-2">
            <div className="col-header" style={{ color: '#4ade80', opacity: 1 }}>New Key Issued — Copy Now</div>
            <button onClick={() => setNewKeyResult(null)} className="text-xs" style={{ color: 'var(--text-dim)' }}>Dismiss</button>
          </div>
          <p className="text-xs mb-3" style={{ color: 'var(--text-dim)' }}>
            This key will NOT be shown again. Store it securely in Secret Manager or your environment.
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 px-3 py-2 rounded text-sm font-mono break-all"
              style={{ background: 'rgba(0,0,0,0.4)', border: '1px solid rgba(255,255,255,0.08)', color: '#4ade80' }}>
              {newKeyResult.api_key}
            </code>
            <button
              onClick={() => navigator.clipboard.writeText(newKeyResult.api_key)}
              className="px-3 py-2 rounded text-xs transition-opacity hover:opacity-80"
              style={{ background: 'rgba(74,222,128,0.15)', border: '1px solid rgba(74,222,128,0.3)', color: '#4ade80' }}
            >
              Copy
            </button>
          </div>
          <div className="mt-2 text-xs" style={{ color: 'var(--text-dim)' }}>
            Issued for: <span style={{ color: 'var(--text)' }}>{newKeyResult.service_name}</span>
          </div>
        </div>
      )}

      {/* Issue new key */}
      <div className="glass-panel p-5 mb-6">
        <div className="col-header mb-3">Issue New Key</div>
        <div className="flex gap-3 flex-wrap items-end">
          <div>
            <div className="text-xs mb-1" style={{ color: 'var(--text-dim)' }}>Service Name *</div>
            <input
              className="px-3 py-1.5 rounded-lg text-sm w-48"
              style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--text)' }}
              placeholder="e.g. fsu4-processor"
              value={form.service_name}
              onChange={e => setForm(f => ({ ...f, service_name: e.target.value }))}
            />
          </div>
          <div>
            <div className="text-xs mb-1" style={{ color: 'var(--text-dim)' }}>Description</div>
            <input
              className="px-3 py-1.5 rounded-lg text-sm w-52"
              style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--text)' }}
              placeholder="Optional description"
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            />
          </div>
          <button
            onClick={handleCreate}
            disabled={creating || !form.service_name.trim()}
            className="px-4 py-1.5 rounded-lg text-sm font-medium transition-opacity hover:opacity-80 disabled:opacity-40"
            style={{ background: 'rgba(0,212,255,0.15)', border: '1px solid rgba(0,212,255,0.3)', color: 'var(--cyan)' }}
          >
            {creating ? 'Issuing…' : 'Issue Key'}
          </button>
        </div>
      </div>

      {/* Key list */}
      <div className="glass-panel overflow-hidden">
        <div className="px-5 py-3 col-header" style={{ borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
          Issued Keys ({keys.length})
        </div>
        {keys.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm" style={{ color: 'var(--text-dim)' }}>
            No keys issued yet
          </div>
        ) : keys.map(key => (
          <div key={key.key_id}
            className="flex items-center gap-4 px-5 py-3"
            style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', opacity: key.active ? 1 : 0.4 }}>
            <div className="w-2 h-2 rounded-full flex-shrink-0"
              style={{ background: key.active ? 'var(--green)' : 'var(--red)' }} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm" style={{ color: 'var(--text)' }}>{key.service_name}</span>
                {!key.active && (
                  <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: 'rgba(255,107,107,0.1)', color: 'var(--red)' }}>
                    revoked
                  </span>
                )}
              </div>
              <div className="text-xs mt-0.5 font-mono" style={{ color: 'var(--text-dim)' }}>
                {key.key_prefix} · issued by {key.issued_by} · {key.created_at ? new Date(key.created_at).toLocaleDateString('en-GB') : ''}
              </div>
              {key.description && (
                <div className="text-xs mt-0.5" style={{ color: 'var(--text-dim)' }}>{key.description}</div>
              )}
            </div>
            <div className="text-xs text-right" style={{ color: 'var(--text-dim)' }}>
              {key.last_used_at ? `Last used ${new Date(key.last_used_at).toLocaleDateString('en-GB')}` : 'Never used'}
            </div>
            {key.active && (
              <button
                onClick={() => handleRevoke(key.key_id)}
                className="text-xs transition-opacity hover:opacity-80"
                style={{ color: 'var(--red)' }}
              >
                Revoke
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
