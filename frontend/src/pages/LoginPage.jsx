import { GoogleLogin } from '@react-oauth/google'
import { useAuth } from '../contexts/AuthContext'

export default function LoginPage() {
  const { login } = useAuth()

  return (
    <div className="relative z-10 flex h-screen items-center justify-center">
      <div className="glass-panel p-10 w-80 text-center">
        <div className="col-header mb-1">Chimera Platform</div>
        <div className="gradient-text text-3xl font-bold mb-1">FSU4C</div>
        <div className="text-sm mb-8" style={{ color: 'var(--text-dim)' }}>
          Chat Intelligence
        </div>

        <div className="flex justify-center">
          <GoogleLogin
            onSuccess={login}
            onError={() => console.error('Login failed')}
            theme="filled_black"
            shape="rectangular"
            text="signin_with"
          />
        </div>

        <p className="text-xs mt-6" style={{ color: 'var(--text-dim)' }}>
          Restricted to ascotwm.com accounts
        </p>
      </div>
    </div>
  )
}
