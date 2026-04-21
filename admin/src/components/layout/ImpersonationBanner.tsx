import { useNavigate } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'
import { useAuthStore } from '@/stores/auth'
import api from '@/lib/api'

export default function ImpersonationBanner() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const navigate = useNavigate()

  if (!user?.is_impersonated) return null

  const handleStopImpersonation = async () => {
    try {
      await api.post('/users/stop-impersonation')
      // After stopping, the response should contain the original admin user.
      // For safety, log out and redirect to login so the admin can re-authenticate.
      logout()
      navigate('/login')
    } catch {
      // Fallback: just log out
      logout()
      navigate('/login')
    }
  }

  return (
    <div
      className="animate-in slide-in-from-top relative z-50 flex items-center justify-center gap-3 bg-amber-500 px-4 py-2 text-sm font-medium text-white shadow-md"
      style={{ animation: 'slideDown 0.3s ease-out' }}
    >
      <AlertTriangle className="h-4 w-4 shrink-0" />
      <span>
        You are viewing as <strong>{user.email}</strong>
      </span>
      <span className="hidden sm:inline">—</span>
      <button
        onClick={handleStopImpersonation}
        className="rounded-md bg-white/20 px-3 py-0.5 text-xs font-semibold text-white transition-colors hover:bg-white/30"
      >
        Return to your account
      </button>

      <style>{`
        @keyframes slideDown {
          from { transform: translateY(-100%); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
      `}</style>
    </div>
  )
}
