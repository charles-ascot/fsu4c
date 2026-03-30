const colours = {
  complete:   { bg: 'rgba(74,222,128,0.12)',  text: '#4ade80' },
  processing: { bg: 'rgba(0,212,255,0.12)',   text: '#00D4FF' },
  pending:    { bg: 'rgba(250,204,21,0.12)',  text: '#facc15' },
  skipped:    { bg: 'rgba(136,136,136,0.12)', text: '#888' },
  failed:     { bg: 'rgba(255,107,107,0.12)', text: '#FF6B6B' },
}

export default function StatusBadge({ value }) {
  const c = colours[value] ?? colours.pending
  return (
    <span
      className="px-2 py-0.5 rounded text-xs font-medium"
      style={{ background: c.bg, color: c.text }}
    >
      {value}
    </span>
  )
}
