import { useMemo } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

const candidateLinks = [
  { to: '/candidate/signup', label: 'Signup' },
  { to: '/candidate/feed', label: 'Feed' },
  { to: '/candidate/matches', label: 'Matches' },
  { to: '/candidate/interview/demo-match', label: 'Interview' },
]

const recruiterLinks = [
  { to: '/recruiter/dashboard', label: 'Dashboard' },
  { to: '/recruiter/roles', label: 'Roles' },
]

function getNavClasses(isActive: boolean) {
  return [
    'rounded-full border px-4 py-2 text-sm font-medium transition-colors duration-200',
    isActive
      ? 'border-navButtonActive bg-navButtonActive text-navButtonText'
      : 'border-navButton bg-navButton text-navButtonText hover:border-navButtonHover hover:bg-navButtonHover',
  ].join(' ')
}

export function AppLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const audience = location.pathname.startsWith('/recruiter')
    ? 'recruiter'
    : 'candidate'

  const links = useMemo(
    () => (audience === 'candidate' ? candidateLinks : recruiterLinks),
    [audience],
  )

  return (
    <div className="min-h-screen bg-pomelo-wash text-textPrimary">
      <header className="sticky top-0 z-10 border-b border-border/70 bg-background/75 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex flex-col gap-4 rounded-3xl border border-white/70 bg-white/70 px-4 py-4 shadow-glass sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.32em] text-textSecondary">
                Pomelo
              </p>
              <h1 className="mt-2 text-2xl font-semibold text-textPrimary">
                AI-assisted hiring platform
              </h1>
              <p className="mt-2 max-w-2xl text-sm text-textSecondary">
                Structured matching, guided interviews, and recruiter-side live decision support.
              </p>
            </div>

            <div className="inline-flex w-full rounded-full border border-border bg-surfaceAlt p-1 shadow-sm sm:w-auto">
              <button
                type="button"
                onClick={() => navigate('/candidate/signup')}
                className={[
                  'flex-1 rounded-full px-4 py-2 text-sm font-medium transition sm:flex-none',
                  audience === 'candidate'
                    ? 'bg-accentPrimary text-navButtonText shadow-sm'
                    : 'text-textSecondary hover:text-textPrimary',
                ].join(' ')}
              >
                Candidate
              </button>
              <button
                type="button"
                onClick={() => navigate('/recruiter/dashboard')}
                className={[
                  'flex-1 rounded-full px-4 py-2 text-sm font-medium transition sm:flex-none',
                  audience === 'recruiter'
                    ? 'bg-accentSecondary text-textPrimary shadow-sm'
                    : 'text-textSecondary hover:text-textPrimary',
                ].join(' ')}
              >
                Recruiter
              </button>
            </div>
          </div>

          <nav className="flex flex-wrap gap-2 rounded-3xl border border-border bg-surface/80 p-3 shadow-panel">
            {links.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) => getNavClasses(isActive)}
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="w-full rounded-[2rem] border border-border bg-surface/90 p-8 shadow-panel">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
