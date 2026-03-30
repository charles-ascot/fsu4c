const BASE = import.meta.env.VITE_API_URL
const KEY = import.meta.env.VITE_API_KEY

const headers = () => ({
  'Content-Type': 'application/json',
  'X-Chimera-API-Key': KEY,
})

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options)
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  // System
  health: () => fetch(`${BASE}/health`).then(r => r.json()),
  status: () => req('/status'),
  version: () => req('/version'),

  // Registry
  getRegistry: (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return req(`/v1/registry${q ? '?' + q : ''}`, { headers: headers() })
  },
  getRecord: (id) => req(`/v1/registry/${id}`, { headers: headers() }),
  getMetrics: () => req('/v1/registry/metrics', { headers: headers() }),

  // Ingest
  manualPoll: (data = {}) => req('/v1/ingest/manual', {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  }),
  getQueue: () => req('/v1/ingest/queue', { headers: headers() }),

  // Spaces
  getSpaces: () => req('/v1/spaces', { headers: headers() }),
  discoverSpaces: () => req('/v1/spaces/discover', {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify({}),
  }),
  registerSpace: (data) => req('/v1/spaces', {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  }),
  deleteSpace: (id) => req(`/v1/spaces/${id}`, {
    method: 'DELETE',
    headers: headers(),
  }),

  // Config
  getConfig: () => req('/v1/config', { headers: headers() }),
  updateConfig: (data) => req('/v1/config', {
    method: 'PUT',
    headers: headers(),
    body: JSON.stringify(data),
  }),

  // API Keys
  getApiKeys: () => req('/v1/auth/keys', { headers: headers() }),
  createApiKey: (data) => req('/v1/auth/keys', {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(data),
  }),
  revokeApiKey: (id) => req(`/v1/auth/keys/${id}`, {
    method: 'DELETE',
    headers: headers(),
  }),
}
