import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import LoadingSpinner from '../components/LoadingSpinner'
import StatusBadge from '../components/StatusBadge'

export default function RegistryPage() {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filters, setFilters] = useState({ status: '', sender: '', limit: 50 })

  const load = () => {
    setLoading(true)
    const params = {}
    if (filters.status) params.status = filters.status
    if (filters.sender) params.sender = filters.sender
    params.limit = filters.limit
    api.getRegistry(params)
      .then(r => setRecords(r.data?.records ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  return (
    <div className="max-w-5xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="gradient-text text-2xl font-bold">Registry</h1>
          <p className="text-xs mt-0.5" style={{ color: 'var(--text-dim)' }}>All ingested Chat messages</p>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-panel p-4 mb-6 flex flex-wrap gap-3 items-end">
        <div>
          <div className="col-header mb-1">Status</div>
          <select
            className="px-3 py-1.5 rounded-lg text-sm"
            style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--text)' }}
            value={filters.status}
            onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}
          >
            <option value="">All</option>
            <option value="complete">complete</option>
            <option value="processing">processing</option>
            <option value="pending">pending</option>
            <option value="failed">failed</option>
            <option value="skipped">skipped</option>
          </select>
        </div>
        <div>
          <div className="col-header mb-1">Sender Email</div>
          <input
            className="px-3 py-1.5 rounded-lg text-sm w-52"
            style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--text)' }}
            placeholder="sender@example.com"
            value={filters.sender}
            onChange={e => setFilters(f => ({ ...f, sender: e.target.value }))}
          />
        </div>
        <button
          onClick={load}
          className="px-4 py-1.5 rounded-lg text-sm font-medium transition-opacity hover:opacity-80"
          style={{ background: 'rgba(0,212,255,0.15)', border: '1px solid rgba(0,212,255,0.3)', color: 'var(--cyan)' }}
        >
          Search
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center pt-20"><LoadingSpinner size={8} /></div>
      ) : error ? (
        <div className="glass-panel p-6 text-center text-sm" style={{ color: 'var(--red)' }}>{error}</div>
      ) : (
        <div className="glass-panel overflow-hidden">
          <div className="px-5 py-3 text-xs" style={{ borderBottom: '1px solid rgba(255,255,255,0.08)', color: 'var(--text-dim)' }}>
            {records.length} record{records.length !== 1 ? 's' : ''}
          </div>
          {records.length === 0 ? (
            <div className="px-5 py-10 text-center text-sm" style={{ color: 'var(--text-dim)' }}>No records found</div>
          ) : records.map(rec => (
            <Link key={rec.record_id} to={`/registry/${rec.record_id}`}
              className="flex items-center gap-4 px-5 py-3 transition-colors hover:bg-white/5"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
              <div className="flex-1 min-w-0">
                <div className="text-sm truncate" style={{ color: 'var(--text)' }}>
                  {rec.message_text?.slice(0, 80) || '(no text)'}
                </div>
                <div className="text-xs mt-0.5" style={{ color: 'var(--text-dim)' }}>
                  {rec.sender_name} · {rec.space_display_name}
                </div>
              </div>
              <StatusBadge value={rec.status} />
              <div className="text-xs whitespace-nowrap" style={{ color: 'var(--text-dim)' }}>
                {rec.received_at ? new Date(rec.received_at).toLocaleString('en-GB') : ''}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
