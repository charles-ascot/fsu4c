import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import AppShell from './components/AppShell'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import RegistryPage from './pages/RegistryPage'
import RecordDetailPage from './pages/RecordDetailPage'
import SpacesPage from './pages/SpacesPage'
import ConfigPage from './pages/ConfigPage'
import ApiKeysPage from './pages/ApiKeysPage'

function AuthGate() {
  const { user } = useAuth()
  if (!user) return <LoginPage />
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/registry" element={<RegistryPage />} />
        <Route path="/registry/:id" element={<RecordDetailPage />} />
        <Route path="/spaces" element={<SpacesPage />} />
        <Route path="/config" element={<ConfigPage />} />
        <Route path="/api-keys" element={<ApiKeysPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AppShell>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AuthGate />
      </BrowserRouter>
    </AuthProvider>
  )
}
