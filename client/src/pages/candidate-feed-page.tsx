import { createRef, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { RefObject } from 'react'
import type {
  SwipeDirection as TinderSwipeDirection,
  TinderCardHandle,
} from '../components/tinder-card'
import TinderCard from '../components/tinder-card'
import { Link } from 'react-router-dom'
import { apiFetch } from '../lib/api'
import { useAuth } from '../contexts/auth-context'

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
  return apiFetch<FeedRole[]>(`/api/candidates/${candidateId}/feed`)
}

async function postSwipe(candidateId: number, roleId: number, intent: SwipeIntent) {
  return apiFetch<SwipeResponse>('/api/swipes', {
    method: 'POST',
    body: {
      candidate_id: candidateId,
      role_id: roleId,
      direction: intent,
      side: 'candidate' as const,
    },
  })
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
  const { session } = useAuth()
  const candidateId = useMemo(() => session?.candidate_id ?? null, [session])
  const [roles, setRoles] = useState<FeedRole[]>([])
  const [activeIndex, setActiveIndex] = useState(-1)
  const [expandedRoleId, setExpandedRoleId] = useState<number | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [feedError, setFeedError] = useState<string | null>(null)
  const [swipeError, setSwipeError] = useState<string | null>(null)
  const [swipesRemaining, setSwipesRemaining] = useState(DAILY_SWIPE_LIMIT)
  const [matchState, setMatchState] = useState<{
    open: boolean
    roleTitle: string
    matchId: number | null
  }>({
    open: false,
    roleTitle: '',
    matchId: null,
  })
  const [comeBackTomorrow, setComeBackTomorrow] = useState(false)
  const refs = useRef<RefObject<TinderCardApi>[]>([])
  const processedRoleIds = useRef<Set<number>>(new Set())

  const loadFeed = useCallback(
    async (showLoading = true) => {
      if (showLoading) {
        setIsLoading(true)
      }

      setFeedError(null)

      if (!candidateId) {
        setFeedError('Create your candidate profile first so we can build your feed.')
        setIsLoading(false)
        return
      }

      try {
        const response = await fetchCandidateFeed(candidateId)
        processedRoleIds.current.clear()
        setRoles(response)
        setActiveIndex(Math.max(response.length - 1, 0))
      } catch (error) {
        setFeedError(getFeedErrorMessage(error))
      } finally {
        if (showLoading) {
          setIsLoading(false)
        }
      }
    },
    [candidateId],
  )

  useEffect(() => {
    void loadFeed()
  }, [loadFeed])

  refs.current = roles.map(
    (_, index) => refs.current[index] ?? createRef(),
  )

  async function handleSwipe(direction: SwipeDirection, role: FeedRole, cardIndex: number) {
    if (!candidateId || processedRoleIds.current.has(role.role_id)) {
      return
    }

    processedRoleIds.current.add(role.role_id)
    setSwipeError(null)
    setExpandedRoleId((current) => (current === role.role_id ? null : current))

    try {
      const response = await postSwipe(
        candidateId,
        role.role_id,
        direction === 'right' ? 'like' : 'pass',
      )

      setSwipesRemaining((current) => Math.max(0, current - 1))
      setComeBackTomorrow(false)

      if (response.matched) {
        setMatchState({ open: true, roleTitle: role.title, matchId: response.match_id ?? null })
      }
    } catch (error) {
      processedRoleIds.current.delete(role.role_id)
      const cardRef = refs.current[cardIndex]?.current

      if (error instanceof Error && error.message.includes('status 429')) {
        await cardRef?.restoreCard()
        setActiveIndex(cardIndex)
        setComeBackTomorrow(true)
        setSwipesRemaining(0)
        return
      }

      await cardRef?.restoreCard()
      setActiveIndex(cardIndex)
      setSwipeError(getFeedErrorMessage(error))
      if (!cardRef) {
        void loadFeed(false)
      }
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
        <p className="type-kicker">
          Candidate feed
        </p>
        <h2 className="type-display-page mt-5">
          Loading your curated role feed...
        </h2>
      </section>
    )
  }

  if (feedError) {
    return (
      <section className="mx-auto max-w-3xl rounded-[2rem] border border-border bg-surface p-10 shadow-panel">
        <p className="type-kicker">
          Candidate feed
        </p>
        <h2 className="type-display-page mt-5">
          Your feed is not ready yet
        </h2>
        <p className="type-body mt-5">{feedError}</p>
        <Link
          to="/candidate/signup"
          className="font-ui mt-8 inline-flex rounded-full border border-navButtonActive bg-navButtonActive px-5 py-3 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover"
        >
          Back to signup
        </Link>
      </section>
    )
  }

  if (!roles.length) {
    return (
      <section className="mx-auto max-w-3xl rounded-[2rem] border border-border bg-surface p-10 shadow-panel">
        <p className="type-kicker">Candidate feed</p>
        <h2 className="type-display-page mt-5">No roles available right now</h2>
        <p className="type-body mt-5">
          You&apos;ve cleared the current stack. Check back soon for more curated roles — and see
          if any recruiters have already matched with you.
        </p>
        <Link
          to="/candidate/matches"
          className="font-ui mt-8 inline-flex rounded-full border border-navButtonActive bg-navButtonActive px-5 py-3 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover"
        >
          View your matches
        </Link>
      </section>
    )
  }

  return (
    <section className="mx-auto flex max-w-6xl flex-col gap-6">
      <div className="flex flex-col gap-4 rounded-[2rem] border border-border bg-surface px-5 py-5 shadow-panel sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="type-kicker">
            Candidate feed
          </p>
          <h2 className="type-display-section mt-3 max-w-2xl">
            Curated roles matched to your resume profile
          </h2>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="font-ui rounded-full border border-border bg-surfaceAlt px-4 py-2 text-sm font-medium text-textPrimary">
            {comeBackTomorrow
              ? "You've used today's swipes"
              : `${swipesRemaining} swipes remaining`}
          </div>
          {comeBackTomorrow ? (
            <Link
              to="/candidate/matches"
              className="font-ui inline-flex items-center justify-center rounded-full border border-navButtonActive bg-navButtonActive px-4 py-2 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover"
            >
              View your matches →
            </Link>
          ) : null}
          {swipeError ? (
            <div className="font-ui rounded-full border border-error/30 bg-error/10 px-4 py-2 text-sm font-medium text-error">
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
                    void handleSwipe(direction, role, index)
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
                        <h3 className="font-display text-[1.65rem] font-semibold tracking-[-0.01em] text-textPrimary">
                          {role.title}
                        </h3>
                        <p className="type-meta mt-1">
                          {getCompanyLabel(role)}
                        </p>
                      </div>
                    </div>

                    <span
                      className={`type-badge inline-flex rounded-full border px-3 py-1 ${getMatchBadgeClasses(matchPercent)}`}
                    >
                      {matchPercent}% match
                    </span>
                  </div>

                  <div className="mt-6 rounded-[1.5rem] border border-border bg-surfaceAlt p-4">
                    <p className="font-ui text-xs uppercase tracking-[0.24em] text-textSecondary">
                      Why this role
                    </p>
                    <p
                      className="font-ui mt-4 text-base leading-7 text-textSecondary"
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
                      className="font-ui mt-5 text-sm font-medium text-navButton hover:text-navButtonHover"
                    >
                      {isExpanded ? 'Show less' : 'Tap to expand'}
                    </button>
                  </div>

                  <div className="font-ui mt-auto grid grid-cols-2 gap-3 pt-8 text-sm text-textSecondary">
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
            className="font-ui flex h-16 w-16 items-center justify-center rounded-full border border-error/30 bg-error/12 text-error transition hover:bg-error/18 disabled:cursor-not-allowed disabled:opacity-50"
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
            className="font-ui flex h-16 w-16 items-center justify-center rounded-full border border-success/30 bg-success/15 text-success transition hover:bg-success/20 disabled:cursor-not-allowed disabled:opacity-50"
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
            <p className="type-kicker text-center">Mutual interest</p>
            <h3 className="font-display mt-5 text-5xl font-semibold tracking-[-0.01em] text-textPrimary">
              It&apos;s a Match!
            </h3>
            <p className="type-body mt-5 text-center">
              You and the recruiter both liked{' '}
              <span className="font-semibold text-textPrimary">{matchState.roleTitle}</span>.
              Head to your matches to begin the interview when it&apos;s ready.
            </p>
            <div className="mt-9 flex flex-col gap-3 sm:flex-row sm:justify-center">
              <Link
                to="/candidate/matches"
                onClick={() =>
                  setMatchState({ open: false, roleTitle: '', matchId: null })
                }
                className="font-ui inline-flex items-center justify-center rounded-full border border-navButtonActive bg-navButtonActive px-5 py-3 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover"
              >
                View my matches
              </Link>
              <button
                type="button"
                onClick={() =>
                  setMatchState({ open: false, roleTitle: '', matchId: null })
                }
                className="font-ui inline-flex items-center justify-center rounded-full border border-border bg-surfaceAlt px-5 py-3 text-sm font-semibold text-textPrimary transition hover:border-accentSecondary hover:bg-accentSecondary/12"
              >
                Keep swiping
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  )
}
