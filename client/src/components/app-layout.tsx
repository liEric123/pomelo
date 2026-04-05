import { useMemo, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/auth-context'

const candidateLinks = [
  { to: '/candidate/signup', label: 'Signup' },
  { to: '/candidate/feed', label: 'Feed' },
  { to: '/candidate/matches', label: 'Matches' },
]

const recruiterLinks = [
  { to: '/recruiter/dashboard', label: 'Dashboard' },
  { to: '/recruiter/roles', label: 'Roles' },
]

function getNavClasses(isActive: boolean) {
  return [
    'font-ui rounded-full border px-4 py-2 text-sm font-medium transition-colors duration-200',
    isActive
      ? 'border-navButtonActive bg-navButtonActive text-navButtonText'
      : 'border-navButton bg-navButton text-navButtonText hover:border-navButtonHover hover:bg-navButtonHover',
  ].join(' ')
}

export function AppLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { session, isAuthenticated, isCandidate, logout } = useAuth()
  const [isHeaderVisible, setIsHeaderVisible] = useState(false)
  const audience = location.pathname.startsWith('/recruiter')
    ? 'recruiter'
    : 'candidate'
  const hideTopBar = location.pathname.startsWith('/candidate/interview/')
  const showNavigation = !(audience === 'candidate' && !isAuthenticated)
  const headerClasses = [
    'pointer-events-auto fixed inset-x-0 top-0 z-30 border-b border-border/70 bg-background/82 backdrop-blur-xl transition-all duration-500 ease-out',
    isHeaderVisible
      ? 'translate-y-0 opacity-100'
      : '-translate-y-[calc(100%-0.9rem)] opacity-0',
  ].join(' ')

  const links = useMemo(
    () =>
      audience === 'candidate'
        ? candidateLinks.filter((link) =>
            isCandidate ? link.to !== '/candidate/signup' : true,
          )
        : recruiterLinks,
    [audience, isCandidate],
  )

  const shellPaddingClasses = hideTopBar ? 'p-4 sm:p-5' : 'p-8'
  const mainPaddingClasses = hideTopBar ? 'py-4' : 'py-12'

  const headerContent = (
    <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
      <nav className="flex flex-wrap items-center gap-x-2 gap-y-3 rounded-3xl border border-border bg-surface/80 p-3 shadow-panel">
        <div className="mr-3 flex shrink-0 items-center px-1">
          <p className="text-xl uppercase tracking-[0.32em] text-textSecondary sm:text-2xl">
            Pomelo
          </p>
        </div>

        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            className={({ isActive }) => getNavClasses(isActive)}
          >
            {link.label}
          </NavLink>
        ))}

        {isAuthenticated && session ? (
          <div className="ml-auto flex flex-wrap items-center justify-end gap-2">
            <span className="font-ui rounded-full border border-border bg-surfaceAlt px-3 py-1.5 text-xs text-textSecondary">
              {session.email?.split('@')[0] ?? session.role}
              <span className="ml-1.5 font-medium text-textPrimary capitalize">
                · {session.role}
              </span>
            </span>
            <button
              type="button"
              onClick={() => {
                logout()
                navigate('/login', { replace: true })
              }}
              className="font-ui rounded-full border border-border bg-surface px-3 py-1.5 text-xs text-textSecondary transition hover:border-error/40 hover:bg-error/10 hover:text-error"
            >
              Sign out
            </button>
          </div>
        ) : null}
      </nav>
    </div>
  )

  return (
    <div className="min-h-screen bg-pomelo-wash text-textPrimary">
      {showNavigation ? (
        <div
          className="fixed inset-x-0 top-0 z-30"
          onMouseEnter={() => setIsHeaderVisible(true)}
          onMouseLeave={() => setIsHeaderVisible(false)}
        >
          <div className="absolute inset-x-0 top-0 h-10" />
          <header className={headerClasses}>
            {headerContent}
          </header>
        </div>
      ) : null}

      <main
        className={[
          'mx-auto flex w-full max-w-7xl px-4 sm:px-6 lg:px-8',
          mainPaddingClasses,
        ].join(' ')}
      >
        <div
          className={[
            'w-full rounded-[2rem] border border-border bg-surface/90 shadow-panel',
            shellPaddingClasses,
          ].join(' ')}
        >
          <Outlet />
        </div>
      </main>
    </div>
  )
}
