import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './AuthContext'

export function ProtectedRoute() {
  const { isAuthenticated, isInitializing } = useAuth()

  if (isInitializing) {
    return <div className="route-state">Restoring your session...</div>
  }

  return isAuthenticated ? <Outlet /> : <Navigate to="/login" replace />
}