import { type FormEvent, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/auth-context'

const DEMO_PASSWORD = 'pomelo2026'

const DEMO_ACCOUNTS = [
  {
    label: 'Mira Patel',
    sublabel: 'Candidate · ML Engineer',
    email: 'mira.patel@demo.pomelo.test',
  },
  {
    label: 'Alex Rivera',
    sublabel: 'Candidate · SaaS Engineer',
    email: 'alex.rivera@demo.pomelo.test',
  },
  {
    label: 'OpenAI Recruiter',
    sublabel: 'Recruiter · OpenAI',
    email: 'recruiter@openai.demo.pomelo.test',
  },
  {
    label: 'Goldman Recruiter',
    sublabel: 'Recruiter · Goldman Sachs',
    email: 'recruiter@goldman.demo.pomelo.test',
  },
]

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, isRecruiter, login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  // Already authenticated — redirect to the right home
  if (isAuthenticated) {
    return (
      <Navigate
        to={isRecruiter ? '/recruiter/dashboard' : '/candidate/feed'}
        replace
      />
    )
  }

  const from =
    (location.state as { from?: { pathname: string } } | null)?.from
      ?.pathname ?? null

  function fillDemo(demoEmail: string) {
    setEmail(demoEmail)
    setPassword(DEMO_PASSWORD)
    setError(null)
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()

    if (!email.trim() || !password) {
      setError('Enter your email and password.')
      return
    }

    setError(null)
    setIsLoading(true)

    try {
      const session = await login(email.trim(), password)
      const dest =
        from ?? (session.role === 'recruiter'
          ? '/recruiter/dashboard'
          : '/candidate/feed')
      navigate(dest, { replace: true })
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Login failed. Please try again.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-12">
      {/* Wordmark */}
      <div className="mb-8 text-center">
        <p className="font-ui text-xs uppercase tracking-[0.32em] text-textSecondary">
          Pomelo
        </p>
        <h1 className="mt-2 font-display text-4xl font-semibold tracking-[-0.01em] text-textPrimary">
          AI-assisted hiring
        </h1>
      </div>

      <div className="w-full max-w-md">
        {/* Demo accounts */}
        <div className="mb-6 rounded-[2rem] border border-border bg-surfaceAlt p-5">
          <p className="type-kicker mb-3">Demo accounts</p>
          <div className="grid grid-cols-2 gap-2">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.email}
                type="button"
                onClick={() => fillDemo(account.email)}
                className={[
                  'rounded-2xl border px-3 py-2.5 text-left transition',
                  email === account.email
                    ? 'border-accentPrimary bg-accentPrimary/12'
                    : 'border-border bg-surface hover:border-accentSecondary hover:bg-accentSecondary/12',
                ].join(' ')}
              >
                <p className="font-ui text-xs font-semibold text-textPrimary">
                  {account.label}
                </p>
                <p className="font-ui mt-0.5 text-[0.7rem] leading-tight text-textSecondary">
                  {account.sublabel}
                </p>
              </button>
            ))}
          </div>
          <p className="font-ui mt-3 text-[0.72rem] text-textSecondary">
            Password for all demo accounts:{' '}
            <code className="rounded bg-border/60 px-1 py-0.5 font-mono text-textPrimary">
              {DEMO_PASSWORD}
            </code>
          </p>
        </div>

        {/* Login form */}
        <form
          onSubmit={(e) => void handleSubmit(e)}
          className="rounded-[2rem] border border-border bg-surface p-6 shadow-panel"
        >
          <h2 className="font-display text-2xl font-semibold tracking-[-0.01em] text-textPrimary">
            Sign in
          </h2>

          {error ? (
            <div className="mt-4 rounded-2xl border border-error/30 bg-error/10 px-4 py-3">
              <p className="font-ui text-sm text-error">{error}</p>
            </div>
          ) : null}

          <div className="mt-5 space-y-4">
            <div>
              <label
                htmlFor="login-email"
                className="type-label mb-1.5 block"
              >
                Email
              </label>
              <input
                id="login-email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="font-ui w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-sm text-textPrimary placeholder-textSecondary/60 transition focus:border-accentPrimary focus:outline-none focus:ring-2 focus:ring-accentPrimary/20"
              />
            </div>

            <div>
              <label
                htmlFor="login-password"
                className="type-label mb-1.5 block"
              >
                Password
              </label>
              <input
                id="login-password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="font-ui w-full rounded-2xl border border-border bg-surfaceAlt px-4 py-3 text-sm text-textPrimary placeholder-textSecondary/60 transition focus:border-accentPrimary focus:outline-none focus:ring-2 focus:ring-accentPrimary/20"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="font-ui mt-6 inline-flex w-full items-center justify-center rounded-full border border-navButtonActive bg-navButtonActive px-5 py-3 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading ? 'Signing in…' : 'Sign in'}
          </button>

          <p className="font-ui mt-5 text-center text-sm text-textSecondary">
            New candidate?{' '}
            <Link
              to="/candidate/signup"
              className="font-medium text-textPrimary underline-offset-2 hover:underline"
            >
              Create your profile
            </Link>
          </p>
        </form>
      </div>
    </div>
  )
}
