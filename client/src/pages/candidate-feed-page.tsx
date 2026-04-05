import { createRef, useEffect, useMemo, useRef, useState } from 'react'
import type { RefObject } from 'react'
import type {
  SwipeDirection as TinderSwipeDirection,
  TinderCardHandle,
} from '../components/tinder-card'
import TinderCard from '../components/tinder-card'
import { Link } from 'react-router-dom'
import { apiFetch } from '../lib/api'
import { getStoredCandidateId } from '../lib/candidate-session'

const DAILY_SWIPE_LIMIT = 5

type FeedRole = {
  role_id: number
  title: string
  company_id?: number | null
  company_name?: string | null
  description: string
  match_percent: number
}

type SwipeResponse = {
  matched: boolean
  match_id?: number
}

type SwipeDirection = Extract<TinderSwipeDirection, 'left' | 'right'>
type SwipeIntent = 'pass' | 'like'
type TinderCardApi = TinderCardHandle

function formatMatchPercent(value: number) {
  return Math.round(Math.max(0, Math.min(100, value)))
}

function getMatchBadgeClasses(matchPercent: number) {
  if (matchPercent >= 70) {
    return 'border-success/30 bg-success/15 text-textPrimary'
  }

  if (matchPercent >= 40) {
    return 'border-warning/35 bg-warning/18 text-textPrimary'
  }

  return 'border-error/30 bg-error/12 text-error'
}

function getCompanyLabel(role: FeedRole) {
  if (role.company_name?.trim()) {
    return role.company_name
  }

  if (role.company_id != null) {
    return `Company #${role.company_id}`
  }

  return 'Pomelo hiring partner'
}

async function fetchCandidateFeed(candidateId: number) {
  try {
    return await apiFetch<FeedRole[]>(
      `/api/candidate/feed?candidate_id=${candidateId}`,
    )
  } catch (error) {
    if (error instanceof Error && error.message.includes('status 404')) {
      return apiFetch<FeedRole[]>(`/api/candidates/${candidateId}/feed`)
    }

    throw error
  }
}

async function postSwipe(candidateId: number, roleId: number, intent: SwipeIntent) {
  const payload = {
    candidate_id: candidateId,
    role_id: roleId,
    direction: intent,
    side: 'candidate' as const,
  }

  try {
    return await apiFetch<SwipeResponse>('/api/swipe', {
      method: 'POST',
      body: payload,
    })
  } catch (error) {
    if (error instanceof Error && error.message.includes('status 404')) {
      return apiFetch<SwipeResponse>('/api/swipes', {
        method: 'POST',
        body: payload,
      })
    }

    throw error
  }
}

function getFeedErrorMessage(error: unknown) {
  if (!(error instanceof Error)) {
    return 'We could not load your role feed right now.'
  }

  if (error.message.includes('status 429')) {
    return 'Come back tomorrow'
  }

  const detail = error.message.match(/status \d+(?::\s*)(.*)$/)?.[1]?.trim()
  return detail || 'We could not load your role feed right now.'
}

export function CandidateFeedPage() {
  const candidateId = useMemo(() => getStoredCandidateId(), [])
  const [roles, setRoles] = useState<FeedRole[]>([])
  const [activeIndex, setActiveIndex] = useState(-1)
  const [expandedRoleId, setExpandedRoleId] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [feedError, setFeedError] = useState<string | null>(null)
  const [swipeError, setSwipeError] = useState<string | null>(null)
  const [swipesRemaining, setSwipesRemaining] = useState(DAILY_SWIPE_LIMIT)
  const [matchState, setMatchState] = useState<{ open: boolean; roleTitle: string }>({
    open: false,
    roleTitle: '',
  })
  const [comeBackTomorrow, setComeBackTomorrow] = useState(false)
  const refs = useRef<RefObject<TinderCardApi>[]>([])
  const processedRoleIds = useRef<Set<number>>(new Set())

  useEffect(() => {
    let cancelled = false

    async function loadFeed() {
      if (!candidateId) {
        setFeedError('Create your candidate profile first so we can build your feed.')
        setIsLoading(false)
        return
      }

      try {
        const response = await fetchCandidateFeed(candidateId)
        if (cancelled) {
          return
        }

        processedRoleIds.current.clear()
        setRoles(response)
        setActiveIndex(Math.max(response.length - 1, 0))
      } catch (error) {
        if (!cancelled) {
          setFeedError(getFeedErrorMessage(error))
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false)
        }
      }
    }

    void loadFeed()

    return () => {
      cancelled = true
    }
  }, [candidateId])

  refs.current = roles.map(
    (_, index) => refs.current[index] ?? createRef(),
  )

  async function handleSwipe(direction: SwipeDirection, role: FeedRole) {
    if (!candidateId || processedRoleIds.current.has(role.role_id)) {
      return
    }

    processedRoleIds.current.add(role.role_id)
    setSwipeError(null)
    setExpandedRoleId((current) => (current === role.role_id ? null : current))
    setSwipesRemaining((current) => Math.max(0, current - 1))

    try {
      const response = await postSwipe(
        candidateId,
        role.role_id,
        direction === 'right' ? 'like' : 'pass',
      )

      if (response.matched) {
        setMatchState({ open: true, roleTitle: role.title })
      }
    } catch (error) {
      if (error instanceof Error && error.message.includes('status 429')) {
        setComeBackTomorrow(true)
        setSwipesRemaining(0)
        return
      }

      setSwipeError(getFeedErrorMessage(error))
    }
  }

  function handleCardLeftScreen(cardIndex: number) {
    setActiveIndex((current) => (current === cardIndex ? cardIndex - 1 : current))
  }

  async function triggerSwipe(direction: SwipeDirection) {
    if (activeIndex < 0 || !refs.current[activeIndex]?.current) {
      return
    }

    await refs.current[activeIndex].current?.swipe(direction)
  }

  if (isLoading) {
    return (
      <section className="mx-auto max-w-3xl rounded-[2rem] border border-border bg-surface p-10 text-center shadow-panel">
        <p className="text-sm font-medium uppercase tracking-[0.32em] text-textSecondary">
          Candidate feed
        </p>
        <h2 className="mt-4 text-3xl font-semibold text-textPrimary">
          Loading your curated role feed...
        </h2>
      </section>
    )
  }

  if (feedError) {
    return (
      <section className="mx-auto max-w-3xl rounded-[2rem] border border-border bg-surface p-10 shadow-panel">
        <p className="text-sm font-medium uppercase tracking-[0.32em] text-textSecondary">
          Candidate feed
        </p>
        <h2 className="mt-4 text-3xl font-semibold text-textPrimary">
          Your feed is not ready yet
        </h2>
        <p className="mt-4 text-base leading-7 text-textSecondary">{feedError}</p>
        <Link
          to="/candidate/signup"
          className="mt-8 inline-flex rounded-full border border-navButtonActive bg-navButtonActive px-5 py-3 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover"
        >
          Back to signup
        </Link>
      </section>
    )
  }

  if (!roles.length) {
    return (
      <section className="mx-auto max-w-3xl rounded-[2rem] border border-border bg-surface p-10 shadow-panel">
        <p className="text-sm font-medium uppercase tracking-[0.32em] text-textSecondary">
          Candidate feed
        </p>
        <h2 className="mt-4 text-3xl font-semibold text-textPrimary">
          No roles available right now
        </h2>
        <p className="mt-4 text-base leading-7 text-textSecondary">
          You&apos;ve cleared the current stack. Check back soon for more curated matches.
        </p>
      </section>
    )
  }

  return (
    <section className="mx-auto flex max-w-6xl flex-col gap-6">
      <div className="flex flex-col gap-4 rounded-[2rem] border border-border bg-surface px-5 py-5 shadow-panel sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.32em] text-textSecondary">
            Candidate feed
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-textPrimary">
            Curated roles matched to your resume profile
          </h2>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="rounded-full border border-border bg-surfaceAlt px-4 py-2 text-sm font-medium text-textPrimary">
            {comeBackTomorrow
              ? 'Come back tomorrow'
              : `${swipesRemaining} swipes remaining`}
          </div>
          {swipeError ? (
            <div className="rounded-full border border-error/30 bg-error/10 px-4 py-2 text-sm font-medium text-error">
              {swipeError}
            </div>
          ) : null}
        </div>
      </div>

      <div className="relative mx-auto flex w-full max-w-sm flex-col items-center">
        <div className="relative h-[34rem] w-full">
          {roles.map((role, index) => {
            const matchPercent = formatMatchPercent(role.match_percent)
            const isExpanded = expandedRoleId === role.role_id

            return (
              <TinderCard
                key={role.role_id}
                ref={refs.current[index]}
                preventSwipe={['up', 'down']}
                onSwipe={(direction) => {
                  if (direction === 'left' || direction === 'right') {
                    void handleSwipe(direction, role)
                  }
                }}
                onCardLeftScreen={() => handleCardLeftScreen(index)}
                className="absolute inset-0"
              >
                <article className="flex h-full cursor-grab flex-col rounded-[2rem] border border-border bg-surface p-5 shadow-panel active:cursor-grabbing">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-center gap-4">
                      <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-border bg-accentHighlight text-lg font-semibold text-textPrimary">
                        {role.title.slice(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <h3 className="text-xl font-semibold text-textPrimary">
                          {role.title}
                        </h3>
                        <p className="mt-1 text-sm text-textSecondary">
                          {getCompanyLabel(role)}
                        </p>
                      </div>
                    </div>

                    <span
                      className={`inline-flex rounded-full border px-3 py-1 text-sm font-semibold ${getMatchBadgeClasses(matchPercent)}`}
                    >
                      {matchPercent}% match
                    </span>
                  </div>

                  <div className="mt-6 rounded-[1.5rem] border border-border bg-surfaceAlt p-4">
                    <p className="text-xs uppercase tracking-[0.24em] text-textSecondary">
                      Why this role
                    </p>
                    <p
                      className="mt-3 text-base leading-7 text-textSecondary"
                      style={
                        isExpanded
                          ? undefined
                          : {
                              display: '-webkit-box',
                              WebkitLineClamp: 3,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                            }
                      }
                    >
                      {role.description}
                    </p>
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedRoleId((current) =>
                          current === role.role_id ? null : role.role_id,
                        )
                      }
                      className="mt-4 text-sm font-medium text-navButton hover:text-navButtonHover"
                    >
                      {isExpanded ? 'Show less' : 'Tap to expand'}
                    </button>
                  </div>

                  <div className="mt-auto grid grid-cols-2 gap-3 pt-6 text-sm text-textSecondary">
                    <div className="rounded-2xl border border-border bg-background px-4 py-3">
                      Swipe left to pass
                    </div>
                    <div className="rounded-2xl border border-border bg-background px-4 py-3">
                      Swipe right if interested
                    </div>
                  </div>
                </article>
              </TinderCard>
            )
          })}
        </div>

        <div className="mt-6 flex items-center gap-4">
          <button
            type="button"
            onClick={() => void triggerSwipe('left')}
            disabled={activeIndex < 0 || comeBackTomorrow}
            className="flex h-16 w-16 items-center justify-center rounded-full border border-error/30 bg-error/12 text-error transition hover:bg-error/18 disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Pass"
          >
            <svg
              viewBox="0 0 24 24"
              className="h-7 w-7"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="M6 6 18 18" strokeLinecap="round" />
              <path d="M18 6 6 18" strokeLinecap="round" />
            </svg>
          </button>

          <button
            type="button"
            onClick={() => void triggerSwipe('right')}
            disabled={activeIndex < 0 || comeBackTomorrow}
            className="flex h-16 w-16 items-center justify-center rounded-full border border-success/30 bg-success/15 text-success transition hover:bg-success/20 disabled:cursor-not-allowed disabled:opacity-50"
            aria-label="Interested"
          >
            <svg
              viewBox="0 0 24 24"
              className="h-7 w-7"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              aria-hidden="true"
            >
              <path d="m5 13 4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </div>

      {matchState.open ? (
        <div className="fixed inset-0 z-20 flex items-center justify-center bg-textPrimary/30 px-4 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-[2rem] border border-border bg-surface p-8 text-center shadow-glass">
            <p className="text-sm font-medium uppercase tracking-[0.28em] text-textSecondary">
              Mutual interest
            </p>
            <h3 className="mt-4 text-4xl font-semibold text-textPrimary">
              It&apos;s a Match!
            </h3>
            <p className="mt-4 text-base leading-7 text-textSecondary">
              You and the recruiter both liked <span className="font-semibold text-textPrimary">{matchState.roleTitle}</span>.
            </p>
            <button
              type="button"
              onClick={() => setMatchState({ open: false, roleTitle: '' })}
              className="mt-8 inline-flex rounded-full border border-navButtonActive bg-navButtonActive px-5 py-3 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover"
            >
              Keep swiping
            </button>
          </div>
        </div>
      ) : null}
    </section>
  )
}
