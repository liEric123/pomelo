import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { apiFetch } from '../lib/api'
import { useAuth } from '../contexts/auth-context'

const POLL_INTERVAL_MS = 12000

type MatchStatus = 'pending' | 'interviewing' | 'completed' | 'rejected'

type CandidateMatch = {
  match_id: number
  role_id: number
  role_title: string | null
  company_name: string | null
  status: MatchStatus
  matched_at: string
  completed_at: string | null
  final_score: number | null
  recommendation: string | null
}

function formatDate(iso: string) {
  const d = new Date(iso)
  return Number.isNaN(d.getTime())
    ? 'Recently'
    : new Intl.DateTimeFormat(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }).format(d)
}

function formatScore(score: number | null) {
  if (score == null) return null
  return `${Math.round(Math.max(0, Math.min(1, score)) * 100)}%`
}

function getStatusMeta(status: MatchStatus) {
  switch (status) {
    case 'pending':
      return {
        label: 'Pending',
        classes: 'border-warning/35 bg-warning/15 text-textPrimary',
        description: 'Matched — interview will be ready soon.',
      }
    case 'interviewing':
      return {
        label: 'Interview ready',
        classes: 'border-info/35 bg-info/15 text-textPrimary',
        description: 'Your interview session is active.',
      }
    case 'completed':
      return {
        label: 'Completed',
        classes: 'border-success/35 bg-success/15 text-textPrimary',
        description: 'Interview complete.',
      }
    case 'rejected':
      return {
        label: 'Not progressed',
        classes: 'border-error/30 bg-error/10 text-error',
        description: 'This application did not advance.',
      }
    default:
      return {
        label: status,
        classes: 'border-border bg-surfaceAlt text-textPrimary',
        description: '',
      }
  }
}

function getRecommendationDisplay(rec: string | null) {
  if (!rec) return null
  const n = rec.toLowerCase().trim()
  if (n.includes('strong') && n.includes('yes')) {
    return { text: 'Strong yes', classes: 'text-success font-semibold' }
  }
  if (n.includes('yes') || n.includes('advance')) {
    return { text: 'Advance', classes: 'text-success font-semibold' }
  }
  if (n.includes('maybe')) {
    return { text: 'Maybe', classes: 'text-warning font-semibold' }
  }
  if (n.includes('no') || n.includes('reject')) {
    return { text: 'No', classes: 'text-error font-semibold' }
  }
  return { text: rec, classes: 'text-textPrimary font-semibold' }
}

export function CandidateMatchesPage() {
  const { session } = useAuth()
  const navigate = useNavigate()
  const candidateId = session?.candidate_id ?? null

  const [matches, setMatches] = useState<CandidateMatch[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Track whether we've ever loaded data so refreshes don't blank the page
  const hasLoadedRef = useRef(false)

  function parseError(err: unknown) {
    return err instanceof Error
      ? (err.message.match(/status \d+(?::\s*)(.*)$/)?.[1]?.trim() ?? err.message)
      : 'Could not load your matches.'
  }

  // Initial load — shows full spinner
  useEffect(() => {
    if (!candidateId) {
      setError('No candidate session found.')
      setIsLoading(false)
      return
    }

    let cancelled = false

    async function load() {
      try {
        const data = await apiFetch<CandidateMatch[]>(
          `/api/candidates/${candidateId}/matches`,
        )
        if (!cancelled) {
          setMatches(data)
          hasLoadedRef.current = true
        }
      } catch (err) {
        if (!cancelled) setError(parseError(err))
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    void load()
    return () => {
      cancelled = true
    }
  }, [candidateId])

  // Background polling — silent, never blanks the page
  useEffect(() => {
    if (!candidateId) return

    const id = window.setInterval(async () => {
      try {
        const data = await apiFetch<CandidateMatch[]>(
          `/api/candidates/${candidateId}/matches`,
        )
        setMatches(data)
      } catch {
        // silent — polling failures don't interrupt the UI
      }
    }, POLL_INTERVAL_MS)

    return () => window.clearInterval(id)
  }, [candidateId])

  // Manual refresh — shows button loading state, surfaces errors
  async function handleRefresh() {
    if (!candidateId || isRefreshing) return
    setIsRefreshing(true)
    setError(null)
    try {
      const data = await apiFetch<CandidateMatch[]>(
        `/api/candidates/${candidateId}/matches`,
      )
      setMatches(data)
    } catch (err) {
      setError(parseError(err))
    } finally {
      setIsRefreshing(false)
    }
  }

  // ── loading / error / empty ────────────────────────────────────
  if (isLoading) {
    return (
      <section className="mx-auto max-w-3xl p-10 text-center">
        <p className="type-kicker">Your matches</p>
        <h2 className="type-display-page mt-5">Loading your matches…</h2>
      </section>
    )
  }

  if (error && !hasLoadedRef.current) {
    return (
      <section className="mx-auto max-w-3xl rounded-[2rem] border border-border bg-surface p-10 shadow-panel">
        <p className="type-kicker">Your matches</p>
        <h2 className="type-display-page mt-5">Could not load matches</h2>
        <p className="type-body mt-4">{error}</p>
        <button
          type="button"
          onClick={() => void handleRefresh()}
          className="font-ui mt-8 inline-flex rounded-full border border-navButtonActive bg-navButtonActive px-5 py-3 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover"
        >
          Try again
        </button>
      </section>
    )
  }

  if (!matches.length) {
    return (
      <section className="mx-auto max-w-3xl rounded-[2rem] border border-border bg-surface p-10 shadow-panel">
        <p className="type-kicker">Your matches</p>
        <h2 className="type-display-page mt-5">No matches yet</h2>
        <p className="type-body mt-4">
          Mutual likes become matches. Swipe right on roles you&apos;re
          interested in and check back here once a recruiter likes you back.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link
            to="/candidate/feed"
            className="font-ui inline-flex rounded-full border border-navButtonActive bg-navButtonActive px-5 py-3 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover"
          >
            Browse roles
          </Link>
          <button
            type="button"
            onClick={() => void handleRefresh()}
            disabled={isRefreshing}
            className="font-ui inline-flex rounded-full border border-border bg-surfaceAlt px-5 py-3 text-sm font-semibold text-textPrimary transition hover:border-accentSecondary hover:bg-accentSecondary/12 disabled:opacity-50"
          >
            {isRefreshing ? 'Checking…' : 'Check for matches'}
          </button>
        </div>
      </section>
    )
  }

  const active = matches.filter(
    (m) => m.status === 'pending' || m.status === 'interviewing',
  )
  const completed = matches.filter((m) => m.status === 'completed')
  const rejected = matches.filter((m) => m.status === 'rejected')

  // ── main layout ────────────────────────────────────────────────
  return (
    <section className="mx-auto max-w-4xl space-y-8">
      {/* Header */}
      <div className="rounded-[2rem] border border-border bg-surfaceAlt p-8 shadow-panel">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="type-kicker">Your matches</p>
            <h2 className="type-display-section mt-3">
              {matches.length} match{matches.length !== 1 ? 'es' : ''} found
            </h2>
          </div>
          <button
            type="button"
            onClick={() => void handleRefresh()}
            disabled={isRefreshing}
            className="font-ui mt-1 inline-flex shrink-0 items-center justify-center rounded-full border border-border bg-surface px-4 py-2 text-sm font-semibold text-textPrimary transition hover:border-accentSecondary hover:bg-accentSecondary/12 disabled:opacity-50"
          >
            {isRefreshing ? 'Refreshing…' : 'Refresh'}
          </button>
        </div>

        {error ? (
          <p className="font-ui mt-4 text-sm text-error">{error}</p>
        ) : null}

        <div className="mt-6 grid grid-cols-3 gap-4">
          <div className="rounded-3xl border border-border bg-surface p-4">
            <p className="type-meta">Active</p>
            <p className="type-stat mt-2">{active.length}</p>
          </div>
          <div className="rounded-3xl border border-border bg-surface p-4">
            <p className="type-meta">Completed</p>
            <p className="type-stat mt-2">{completed.length}</p>
          </div>
          <div className="rounded-3xl border border-border bg-surface p-4">
            <p className="type-meta">Not progressed</p>
            <p className="type-stat mt-2">{rejected.length}</p>
          </div>
        </div>
      </div>

      {/* Active matches */}
      {active.length > 0 ? (
        <div className="space-y-4">
          <p className="type-kicker px-1">Active</p>
          <div className="grid gap-4 sm:grid-cols-2">
            {active.map((match) => {
              const status = getStatusMeta(match.status)
              const canEnter =
                match.status === 'interviewing' || match.status === 'pending'
              return (
                <article
                  key={match.match_id}
                  className="flex flex-col rounded-[2rem] border border-border bg-surface p-6 shadow-panel"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="type-meta truncate">
                        {match.company_name ?? 'Pomelo hiring partner'}
                      </p>
                      <h3 className="font-display mt-1.5 text-xl font-semibold tracking-tight text-textPrimary">
                        {match.role_title ?? 'Role'}
                      </h3>
                    </div>
                    <span
                      className={`type-badge shrink-0 rounded-full border px-3 py-1 ${status.classes}`}
                    >
                      {status.label}
                    </span>
                  </div>

                  <p className="font-ui mt-4 text-sm text-textSecondary">
                    Matched {formatDate(match.matched_at)}
                  </p>

                  <div className="mt-auto pt-6">
                    {canEnter ? (
                      <button
                        type="button"
                        onClick={() =>
                          navigate(`/candidate/interview/${match.match_id}`)
                        }
                        className="font-ui inline-flex w-full items-center justify-center rounded-full border border-navButtonActive bg-navButtonActive px-5 py-2.5 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover"
                      >
                        {match.status === 'interviewing'
                          ? 'Continue interview'
                          : 'Begin interview'}
                      </button>
                    ) : (
                      <div className="rounded-2xl border border-border bg-surfaceAlt px-4 py-3">
                        <p className="font-ui text-sm text-textSecondary">
                          {status.description}
                        </p>
                      </div>
                    )}
                  </div>
                </article>
              )
            })}
          </div>
        </div>
      ) : null}

      {/* Completed matches */}
      {completed.length > 0 ? (
        <div className="space-y-4">
          <p className="type-kicker px-1">Completed interviews</p>
          <div className="grid gap-4 sm:grid-cols-2">
            {completed.map((match) => {
              const scoreDisplay = formatScore(match.final_score)
              const rec = getRecommendationDisplay(match.recommendation)
              return (
                <article
                  key={match.match_id}
                  className="flex flex-col rounded-[2rem] border border-border bg-surface p-6 shadow-panel"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="type-meta truncate">
                        {match.company_name ?? 'Pomelo hiring partner'}
                      </p>
                      <h3 className="font-display mt-1.5 text-xl font-semibold tracking-tight text-textPrimary">
                        {match.role_title ?? 'Role'}
                      </h3>
                    </div>
                    <span className="type-badge shrink-0 rounded-full border border-success/35 bg-success/15 px-3 py-1 text-textPrimary">
                      Done
                    </span>
                  </div>

                  {match.completed_at ? (
                    <p className="font-ui mt-3 text-sm text-textSecondary">
                      Completed {formatDate(match.completed_at)}
                    </p>
                  ) : null}

                  <div className="mt-4 grid grid-cols-2 gap-3">
                    <div className="rounded-2xl border border-border bg-surfaceAlt px-4 py-3">
                      <p className="type-meta">Score</p>
                      <p className="font-ui mt-1 text-lg font-semibold text-textPrimary">
                        {scoreDisplay ?? '—'}
                      </p>
                    </div>
                    <div className="rounded-2xl border border-border bg-surfaceAlt px-4 py-3">
                      <p className="type-meta">Outcome</p>
                      {rec ? (
                        <p className={`font-ui mt-1 text-base ${rec.classes}`}>
                          {rec.text}
                        </p>
                      ) : (
                        <p className="font-ui mt-1 text-base text-textSecondary">
                          Pending review
                        </p>
                      )}
                    </div>
                  </div>
                </article>
              )
            })}
          </div>
        </div>
      ) : null}

      {/* Rejected matches — compact list */}
      {rejected.length > 0 ? (
        <div className="space-y-3">
          <p className="type-kicker px-1">Not progressed</p>
          {rejected.map((match) => (
            <div
              key={match.match_id}
              className="flex items-center justify-between gap-4 rounded-[1.5rem] border border-border bg-surface px-5 py-4"
            >
              <div className="min-w-0">
                <p className="font-ui truncate text-sm font-semibold text-textPrimary">
                  {match.role_title ?? 'Role'}
                </p>
                <p className="type-meta mt-0.5 truncate">
                  {match.company_name ?? 'Pomelo hiring partner'}
                </p>
              </div>
              <span className="type-badge shrink-0 rounded-full border border-error/30 bg-error/10 px-3 py-1 text-error">
                Not progressed
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  )
}
