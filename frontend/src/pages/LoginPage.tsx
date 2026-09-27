import { useState, type FormEvent } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { useAuth } from '../auth/AuthContext'

export function LoginPage() {
  const { isAuthenticated, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errorMessage, setErrorMessage] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  if (isAuthenticated) return <Navigate to="/dashboard" replace />

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setErrorMessage('')
    setIsSubmitting(true)
    try {
      await login({ email, password })
      const destination = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? '/dashboard'
      navigate(destination, { replace: true })
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setErrorMessage('The email or password is incorrect.')
      } else if (error instanceof TypeError) {
        setErrorMessage('The platform is unavailable. Check the API connection and try again.')
      } else {
        setErrorMessage('We could not sign you in. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="auth-layout">
      <section className="auth-intro">
        <div className="brand-mark">FT</div>
        <p className="eyebrow">Fleet operations / secure access</p>
        <h1>Telemetry with a clear line of sight.</h1>
        <p className="intro-copy">
          Sign in to manage your organization&apos;s vehicles, trips, and live operations workspace.
        </p>
        <div className="intro-rule" />
        <p className="intro-note">Invite-only platform · authenticated access</p>
      </section>

      <section className="auth-panel" aria-labelledby="login-title">
        <div className="panel-kicker">Operator console</div>
        <h2 id="login-title">Welcome back</h2>
        <p className="panel-copy">Use your invited account to continue.</p>
        <form onSubmit={handleSubmit} className="login-form">
          <label htmlFor="email">Email address</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          {errorMessage && <p className="form-error" role="alert">{errorMessage}</p>}
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </section>
    </main>
  )
}