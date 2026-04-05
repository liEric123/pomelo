import { useMemo, useState } from 'react'
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
    'font-ui rounded-full border px-4 py-2 text-sm font-medium transition-colors duration-200',
    isActive
      ? 'border-navButtonActive bg-navButtonActive text-navButtonText'
      : 'border-navButton bg-navButton text-navButtonText hover:border-navButtonHover hover:bg-navButtonHover',
  ].join(' ')
}

export function AppLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const [isHeaderVisible, setIsHeaderVisible] = useState(false)
  const audience = location.pathname.startsWith('/recruiter')
    ? 'recruiter'
    : 'candidate'
  const hideTopBar = location.pathname.startsWith('/candidate/interview/')
  const headerClasses = [
    'pointer-events-auto fixed inset-x-0 top-0 z-30 border-b border-border/70 bg-background/82 backdrop-blur-xl transition-all duration-500 ease-out',
    isHeaderVisible
      ? 'translate-y-0 opacity-100'
      : '-translate-y-[calc(100%-0.9rem)] opacity-0',
  ].join(' ')

  const links = useMemo(
    () => (audience === 'candidate' ? candidateLinks : recruiterLinks),
    [audience],
  )

  const shellPaddingClasses = hideTopBar ? 'p-4 sm:p-5' : 'p-8'
  const mainPaddingClasses = hideTopBar ? 'py-4' : 'py-12'

  const headerContent = (
    <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:px-6 lg:px-8">
      <div className="flex flex-col gap-4 rounded-3xl border border-white/70 bg-white/70 px-4 py-4 shadow-glass sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.32em] text-textSecondary">
            Pomelo
          </p>
          <h1 className="mt-3 font-display text-3xl font-semibold tracking-[-0.01em] text-textPrimary sm:text-[2.3rem]">
            AI-assisted hiring platform
          </h1>
          <p className="mt-4 max-w-2xl font-ui text-sm leading-6 text-textSecondary">
            Structured matching, guided interviews, and recruiter-side live decision support.
          </p>
        </div>

        <div className="inline-flex w-full rounded-full border border-border bg-surfaceAlt p-1 shadow-sm sm:w-auto">
          <button
            type="button"
            onClick={() => navigate('/candidate/signup')}
            className={[
              'font-ui flex-1 rounded-full px-4 py-2 text-sm font-medium transition sm:flex-none',
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
              'font-ui flex-1 rounded-full px-4 py-2 text-sm font-medium transition sm:flex-none',
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
  )

  return (
    <div className="min-h-screen bg-pomelo-wash text-textPrimary">
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
