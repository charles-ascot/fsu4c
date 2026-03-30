import { useEffect, useState } from 'react'
import { api } from '../api'
import LoadingSpinner from '../components/LoadingSpinner'

export default function ConfigPage() {
  const [config, setConfig] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState(null)
  const [form, setForm] = useState({})

  useEffect(() => {
    api.getConfig()
      .then(r => { setConfig(r.data); setForm(r.data) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const handleSave = () => {
    setSaving(true)
    api.updateConfig(form)
      .then(r => { setConfig(r.data); setForm(r.data); setSaved(true); setTimeout(() => setSaved(false), 2000) })
      .catch(e => setError(e.message))
      .finally(() => setSaving(false))
  }

  if (loading) return <div className="flex justify-center pt-20"><LoadingSpinner size={8} /></div>

  return (
    <div className="max-w-2xl">
      <div className="mb-6">
        <h1 className="gradient-text text-2xl font-bold">Config</h1>
        <p className="text-xs mt-0.5" style={{ color: 'var(--text-dim)' }}>Processing configuration for FSU4C</p>
      </div>

      {error && <div className="glass-panel p-4 mb-4 text-sm" style={{ color: 'var(--red)' }}>{error}</div>}

      <div className="glass-panel p-6 space-y-5">
        <div>
          <div className="col-header mb-1">Poll Interval (minutes)</div>
          <input
            type="number" min="1" max="60"
            className="px-3 py-1.5 rounded-lg text-sm w-28"
            style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--text)' }}
            value={form.poll_interval_minutes ?? 5}
            onChange={e => setForm(f => ({ ...f, poll_interval_minutes: parseInt(e.target.value) || 5 }))}
          />
          <p className="text-xs mt-1" style={{ color: 'var(--text-dim)' }}>Should match Cloud Scheduler interval</p>
        </div>

        <div>
          <div className="col-header mb-1">Max Attachment Size (MB)</div>
          <input
            type="number" min="1"
            className="px-3 py-1.5 rounded-lg text-sm w-28"
            style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--text)' }}
            value={form.max_attachment_size_mb ?? 50}
            onChange={e => setForm(f => ({ ...f, max_attachment_size_mb: parseInt(e.target.value) || 50 }))}
          />
        </div>

        <div>
          <div className="col-header mb-1">Ignore Senders</div>
          <textarea
            className="w-full px-3 py-2 rounded-lg text-sm font-mono"
            style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--text)' }}
            rows={3}
            placeholder="One sender ID or email per line"
            value={(form.ignore_senders ?? []).join('\n')}
            onChange={e => setForm(f => ({ ...f, ignore_senders: e.target.value.split('\n').map(s => s.trim()).filter(Boolean) }))}
          />
        </div>

        <div>
          <div className="col-header mb-1">Ignore Spaces</div>
          <textarea
            className="w-full px-3 py-2 rounded-lg text-sm font-mono"
            style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--text)' }}
            rows={3}
            placeholder="One space resource name per line (e.g. spaces/AAAA1234)"
            value={(form.ignore_spaces ?? []).join('\n')}
            onChange={e => setForm(f => ({ ...f, ignore_spaces: e.target.value.split('\n').map(s => s.trim()).filter(Boolean) }))}
          />
        </div>

        <button
          onClick={handleSave}
          disabled={saving}
          className="px-5 py-2 rounded-lg text-sm font-medium transition-opacity hover:opacity-80 disabled:opacity-40"
          style={{ background: saved ? 'rgba(74,222,128,0.15)' : 'rgba(0,212,255,0.15)', border: `1px solid ${saved ? 'rgba(74,222,128,0.3)' : 'rgba(0,212,255,0.3)'}`, color: saved ? '#4ade80' : 'var(--cyan)' }}
        >
          {saving ? 'Saving…' : saved ? 'Saved ✓' : 'Save Config'}
        </button>
      </div>
    </div>
  )
}
