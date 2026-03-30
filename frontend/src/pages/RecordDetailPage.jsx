import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'
import LoadingSpinner from '../components/LoadingSpinner'
import StatusBadge from '../components/StatusBadge'

function Field({ label, value }) {
  if (value === null || value === undefined || value === '') return null
  return (
    <div>
      <div className="col-header mb-1">{label}</div>
      <div className="text-sm" style={{ color: 'var(--text)' }}>{String(value)}</div>
    </div>
  )
}

export default function RecordDetailPage() {
  const { id } = useParams()
  const [record, setRecord] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.getRecord(id)
      .then(r => setRecord(r.data))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="flex justify-center pt-20"><LoadingSpinner size={8} /></div>
  if (error) return <div className="glass-panel p-6 text-sm" style={{ color: 'var(--red)' }}>{error}</div>
  if (!record) return null

  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-3 mb-6">
        <Link to="/registry" className="text-xs transition-opacity hover:opacity-70" style={{ color: 'var(--text-dim)' }}>
          ← Registry
        </Link>
        <StatusBadge value={record.status} />
      </div>

      <div className="glass-panel p-6 mb-4">
        <div className="col-header mb-4">Message</div>
        <div className="text-sm leading-relaxed whitespace-pre-wrap mb-6"
          style={{ color: 'var(--text)' }}>
          {record.message_text || '(no text content)'}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Sender" value={record.sender_name} />
          <Field label="Sender Email" value={record.sender_email} />
          <Field label="Space" value={record.space_display_name} />
          <Field label="Space Type" value={record.space_type} />
          <Field label="Received" value={record.received_at ? new Date(record.received_at).toLocaleString('en-GB') : ''} />
          <Field label="Record ID" value={record.record_id} />
        </div>
      </div>

      {record.attachments?.length > 0 && (
        <div className="glass-panel p-6 mb-4">
          <div className="col-header mb-3">Attachments ({record.attachments.length})</div>
          <div className="space-y-2">
            {record.attachments.map((att, i) => (
              <div key={i} className="flex items-center gap-3 text-sm px-3 py-2 rounded-lg"
                style={{ background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.06)' }}>
                <span style={{ color: 'var(--cyan)' }}>📎</span>
                <span style={{ color: 'var(--text)' }}>{att.filename || att.attachment_id}</span>
                {att.content_type && (
                  <span className="text-xs ml-auto" style={{ color: 'var(--text-dim)' }}>{att.content_type}</span>
                )}
                <span className="text-xs px-2 py-0.5 rounded"
                  style={{ background: 'rgba(0,212,255,0.1)', color: 'var(--cyan)' }}>
                  {att.source || att.processing_status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="glass-panel p-6">
        <div className="col-header mb-3">Storage</div>
        <div className="space-y-2">
          <Field label="GCS Raw Prefix" value={record.gcs_raw_prefix} />
          <Field label="GCS Processed Prefix" value={record.gcs_processed_prefix} />
          <Field label="Processing Time" value={record.processing_time_ms ? `${record.processing_time_ms}ms` : null} />
          {record.processing_error && (
            <div>
              <div className="col-header mb-1">Processing Error</div>
              <div className="text-sm" style={{ color: 'var(--red)' }}>{record.processing_error}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
