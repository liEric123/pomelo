import type { FormEvent } from 'react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { apiFetch } from '../lib/api'
import { subscribeDashboard } from '../lib/sse'

const DEFAULT_TOTAL_QUESTIONS = 4

type ActiveInterview = {
  match_id: number
  role_id: number
  role_title: string
  candidate_id: number
  candidate_name: string
  top_skills: string[]
  matched_at: string
}

type TranscriptRole = 'question' | 'answer' | 'follow_up' | 'score'

type TranscriptItem = {
  id: string
  role: TranscriptRole
  text: string
  questionId?: string | null
  flagged?: boolean
  score?: number | null
  recruiterHint?: string | null
}

type ScoreEventPayload = {
  question_id?: string | number | null
  score?: number | null
  flag?: string | null
  recruiter_hint?: string | null
}

type FlagEventPayload = {
  question_id?: string | number | null
  detail?: string | null
  flag?: string | null
}

type TranscriptEventPayload = {
  question_id?: string | number | null
  text?: string | null
  role?: 'question' | 'answer' | 'follow_up' | null
}

type InterviewSummary = {
  verdict?: string | null
  confidence?: number | null
  one_liner?: string | null
  strengths?: string[]
  concerns?: string[]
  scores_weighted?: number | null
}

type CompareCandidate = {
  match_id: number
  candidate_id: number
  name: string
  resume_score_pct: number
  interview_score_pct: number
  total_score: number
  recommendation?: string | null
  top_skills: string[]
  completed_at?: string | null
  rank?: number
}

type CompareResponse = {
  advance: CompareCandidate[]
  reject: CompareCandidate[]
  total: number
  cutoff: number
}

type StreamEnvelope = {
  type?: string
  data?: unknown
}

type InterviewPanel = {
  interview: ActiveInterview
  transcript: TranscriptItem[]
  alerts: string[]
  frameSrc: string | null
  questionOrder: string[]
  progressCurrent: number
  progressTotal: number
  injectText: string
  injectPending: boolean
  injectError: string | null
  completed: boolean
  summary: InterviewSummary | null
  streamError: string | null
  endError: string | null
}

type RoleOption = {
  id: number
  label: string
  count: number
}

function createPanel(interview: ActiveInterview): InterviewPanel {
  return {
    interview,
    transcript: [],
    alerts: [],
    frameSrc: null,
    questionOrder: [],
    progressCurrent: 1,
    progressTotal: DEFAULT_TOTAL_QUESTIONS,
    injectText: '',
    injectPending: false,
    injectError: null,
    completed: false,
    summary: null,
    streamError: null,
    endError: null,
  }
}

function getErrorMessage(error: unknown, fallback: string) {
  if (!(error instanceof Error)) {
    return fallback
  }

  const detail = error.message.match(/status \d+(?::\s*)(.*)$/)?.[1]?.trim()
  return detail || fallback
}

function normalizeQuestionId(questionId: string | number | null | undefined) {
  if (questionId == null) {
    return null
  }

  return String(questionId)
}

function formatProgress(current: number, total: number) {
  return `Q${Math.max(1, current)}/${Math.max(1, total)}`
}

function formatTimestamp(value: string) {
  const parsed = new Date(value)

  if (Number.isNaN(parsed.getTime())) {
    return 'Live now'
  }

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(parsed)
}

function formatPercent(value: number) {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`
}

function formatPercentScore(value: number) {
  return `${Math.round(Math.max(0, Math.min(100, value)))}%`
}

function formatWeightedScore(value: number | null | undefined) {
  if (typeof value !== 'number') {
    return null
  }

  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}% weighted`
}

function getScoreBadgeClasses(score: number | null | undefined) {
  if (typeof score !== 'number') {
    return 'border-border bg-surfaceAlt text-textPrimary'
  }

  if (score >= 0.75) {
    return 'border-success/35 bg-success/15 text-textPrimary'
  }

  if (score >= 0.45) {
    return 'border-warning/35 bg-warning/18 text-textPrimary'
  }

  return 'border-error/35 bg-error/12 text-textPrimary'
}

function normalizeFrameSource(raw: unknown) {
  if (typeof raw === 'string') {
    return raw.startsWith('data:image') ? raw : null
  }

  if (!raw || typeof raw !== 'object') {
    return null
  }

  const payload = raw as { base64?: unknown; data?: unknown }

  if (typeof payload.base64 === 'string') {
    return payload.base64.startsWith('data:image')
      ? payload.base64
      : `data:image/jpeg;base64,${payload.base64}`
  }

  if (typeof payload.data === 'string') {
    return payload.data.startsWith('data:image')
      ? payload.data
      : `data:image/jpeg;base64,${payload.data}`
  }

  if (payload.data && typeof payload.data === 'object') {
    return normalizeFrameSource(payload.data)
  }

  return null
}

async function fetchActiveInterviews() {
  return apiFetch<ActiveInterview[]>('/api/recruiter/active-interviews')
}

async function fetchComparison(roleId: number) {
  try {
    return await apiFetch<CompareResponse>(`/api/recruiter/compare?role_id=${roleId}`)
  } catch {
    return apiFetch<CompareResponse>(`/api/recruiter/roles/${roleId}/compare`)
  }
}

async function injectQuestion(matchId: number, questionText: string) {
  try {
    return await apiFetch<{ queued: boolean }>('/api/interview/inject', {
      method: 'POST',
      body: {
        match_id: matchId,
        question_text: questionText,
      },
    })
  } catch {
    return apiFetch<{ queued: boolean }>(`/api/interviews/${matchId}/inject`, {
      method: 'POST',
      body: {
        question_text: questionText,
      },
    })
  }
}

export function RecruiterDashboardPage() {
  const [panels, setPanels] = useState<Record<number, InterviewPanel>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [selectedRoleId, setSelectedRoleId] = useState<string>('all')
  const [isCompareOpen, setIsCompareOpen] = useState(false)
  const [isCompareLoading, setIsCompareLoading] = useState(false)
  const [compareError, setCompareError] = useState<string | null>(null)
  const [comparison, setComparison] = useState<CompareResponse | null>(null)
  const sourcesRef = useRef<Record<number, EventSource>>({})
  const transcriptRefs = useRef<Record<number, HTMLDivElement | null>>({})

  const panelList = useMemo(
    () =>
      Object.values(panels).sort(
        (left, right) => left.interview.match_id - right.interview.match_id,
      ),
    [panels],
  )

  const roleOptions = useMemo<RoleOption[]>(() => {
    const counts = new Map<number, RoleOption>()

    panelList.forEach(({ interview }) => {
      const existing = counts.get(interview.role_id)
      if (existing) {
        existing.count += 1
        return
      }

      counts.set(interview.role_id, {
        id: interview.role_id,
        label: interview.role_title,
        count: 1,
      })
    })

    return Array.from(counts.values()).sort((left, right) =>
      left.label.localeCompare(right.label),
    )
  }, [panelList])

  const visiblePanels = useMemo(() => {
    if (selectedRoleId === 'all') {
      return panelList
    }

    const parsed = Number.parseInt(selectedRoleId, 10)
    if (Number.isNaN(parsed)) {
      return panelList
    }

    return panelList.filter((panel) => panel.interview.role_id === parsed)
  }, [panelList, selectedRoleId])

  const compareRoleId =
    selectedRoleId === 'all'
      ? roleOptions.length === 1
        ? roleOptions[0].id
        : null
      : Number.parseInt(selectedRoleId, 10)

  useEffect(() => {
    async function loadDashboard() {
      setIsLoading(true)
      setLoadError(null)

      try {
        const interviews = await fetchActiveInterviews()

        setPanels((current) => {
          const next: Record<number, InterviewPanel> = {}

          interviews.forEach((interview) => {
            const existing = current[interview.match_id]
            next[interview.match_id] = existing
              ? { ...existing, interview }
              : createPanel(interview)
          })

          return next
        })
      } catch (error) {
        setPanels({})
        setLoadError(
          getErrorMessage(error, 'We could not load active recruiter interviews right now.'),
        )
      } finally {
        setIsLoading(false)
      }
    }

    void loadDashboard()
  }, [])

  useEffect(() => {
    if (selectedRoleId !== 'all') {
      return
    }

    if (roleOptions.length === 1) {
      setSelectedRoleId(String(roleOptions[0].id))
    }
  }, [roleOptions, selectedRoleId])

  useEffect(() => {
    const activeIds = new Set(panelList.map((panel) => panel.interview.match_id))

    panelList.forEach((panel) => {
      const matchId = panel.interview.match_id
      if (sourcesRef.current[matchId]) {
        return
      }

      const source = subscribeDashboard({ path: `/api/interviews/${matchId}/stream` })
      sourcesRef.current[matchId] = source

      source.onmessage = (event) => {
        try {
          const envelope = JSON.parse(event.data) as StreamEnvelope
          const eventType = envelope.type ?? 'unknown'

          if (eventType === 'transcript') {
            const payload = (envelope.data ?? {}) as TranscriptEventPayload
            const text = payload.text?.trim()
            const role = payload.role ?? 'question'
            if (!text) {
              return
            }

            const questionId = normalizeQuestionId(payload.question_id)

            setPanels((current) => {
              const target = current[matchId]
              if (!target) {
                return current
              }

              const nextOrder =
                role === 'question' && questionId && !target.questionOrder.includes(questionId)
                  ? [...target.questionOrder, questionId]
                  : target.questionOrder

              return {
                ...current,
                [matchId]: {
                  ...target,
                  streamError: null,
                  questionOrder: nextOrder,
                  progressCurrent:
                    role === 'question' && questionId
                      ? Math.max(1, nextOrder.length)
                      : target.progressCurrent,
                  progressTotal: Math.max(DEFAULT_TOTAL_QUESTIONS, nextOrder.length),
                  transcript: [
                    ...target.transcript,
                    {
                      id: `${matchId}-${role}-${crypto.randomUUID()}`,
                      role,
                      text,
                      questionId,
                    },
                  ],
                },
              }
            })
            return
          }

          if (eventType === 'score') {
            const payload = (envelope.data ?? {}) as ScoreEventPayload
            const questionId = normalizeQuestionId(payload.question_id)

            setPanels((current) => {
              const target = current[matchId]
              if (!target) {
                return current
              }

              const transcript = [...target.transcript]
              let answerUpdated = false

              for (let index = transcript.length - 1; index >= 0; index -= 1) {
                const item = transcript[index]
                if (item.role === 'answer' && item.questionId === questionId) {
                  transcript[index] = {
                    ...item,
                    flagged: item.flagged || Boolean(payload.flag),
                    score: payload.score ?? null,
                    recruiterHint: payload.recruiter_hint ?? null,
                  }
                  answerUpdated = true
                  break
                }
              }

              if (!answerUpdated) {
                transcript.push({
                  id: `${matchId}-score-${crypto.randomUUID()}`,
                  role: 'score',
                  text:
                    typeof payload.score === 'number'
                      ? `Score ${formatPercent(payload.score)}`
                      : 'Score update',
                  questionId,
                  flagged: Boolean(payload.flag),
                  score: payload.score ?? null,
                  recruiterHint: payload.recruiter_hint ?? null,
                })
              }

              const alerts =
                payload.flag != null
                  ? [`Flagged: ${payload.flag.replaceAll('_', ' ')}`, ...target.alerts].slice(0, 3)
                  : target.alerts

              return {
                ...current,
                [matchId]: {
                  ...target,
                  streamError: null,
                  transcript,
                  alerts,
                },
              }
            })
            return
          }

          if (eventType === 'flag') {
            const payload = (envelope.data ?? {}) as FlagEventPayload
            const questionId = normalizeQuestionId(payload.question_id)
            const detail = payload.detail ?? payload.flag ?? 'Candidate response flagged.'

            setPanels((current) => {
              const target = current[matchId]
              if (!target) {
                return current
              }

              return {
                ...current,
                [matchId]: {
                  ...target,
                  streamError: null,
                  alerts: [detail, ...target.alerts].slice(0, 3),
                  transcript: target.transcript.map((item) =>
                    item.questionId === questionId
                      ? { ...item, flagged: true }
                      : item,
                  ),
                },
              }
            })
            return
          }

          if (eventType === 'frame') {
            const frameSrc = normalizeFrameSource(envelope.data)
            if (!frameSrc) {
              return
            }

            setPanels((current) => {
              const target = current[matchId]
              if (!target) {
                return current
              }

              return {
                ...current,
                [matchId]: {
                  ...target,
                  streamError: null,
                  frameSrc,
                },
              }
            })
            return
          }

          if (eventType === 'interview_complete') {
            const summary =
              (envelope.data as { summary?: InterviewSummary } | undefined)?.summary ?? null

            setPanels((current) => {
              const target = current[matchId]
              if (!target) {
                return current
              }

              return {
                ...current,
                [matchId]: {
                  ...target,
                  completed: true,
                  streamError: null,
                  summary,
                },
              }
            })
          }
        } catch {
          setPanels((current) => {
            const target = current[matchId]
            if (!target) {
              return current
            }

            return {
              ...current,
              [matchId]: {
                ...target,
                streamError: 'We received an unreadable stream update for this interview.',
              },
            }
          })
        }
      }

      source.onerror = () => {
        setPanels((current) => {
          const target = current[matchId]
          if (!target) {
            return current
          }

          return {
            ...current,
            [matchId]: {
              ...target,
              streamError:
                'Live updates paused. This repo currently streams per interview from the server, and the connection could not be maintained.',
            },
          }
        })
      }
    })

    Object.entries(sourcesRef.current).forEach(([key, source]) => {
      const matchId = Number(key)
      if (!activeIds.has(matchId)) {
        source.close()
        delete sourcesRef.current[matchId]
      }
    })

    return () => {
      Object.values(sourcesRef.current).forEach((source) => source.close())
      sourcesRef.current = {}
    }
  }, [panelList])

  useEffect(() => {
    visiblePanels.forEach((panel) => {
      const viewport = transcriptRefs.current[panel.interview.match_id]
      if (viewport) {
        viewport.scrollTop = viewport.scrollHeight
      }
    })
  }, [visiblePanels])

  async function handleInjectQuestion(matchId: number, event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const panel = panels[matchId]
    const questionText = panel?.injectText.trim()

    if (!panel || !questionText) {
      setPanels((current) => ({
        ...current,
        [matchId]: current[matchId]
          ? {
              ...current[matchId],
              injectError: 'Enter a follow-up question before sending it.',
            }
          : current[matchId],
      }))
      return
    }

    setPanels((current) => ({
      ...current,
      [matchId]: {
        ...current[matchId],
        injectPending: true,
        injectError: null,
      },
    }))

    try {
      await injectQuestion(matchId, questionText)
      setPanels((current) => ({
        ...current,
        [matchId]: {
          ...current[matchId],
          injectPending: false,
          injectText: '',
        },
      }))
    } catch (error) {
      setPanels((current) => ({
        ...current,
        [matchId]: {
          ...current[matchId],
          injectPending: false,
          injectError: getErrorMessage(
            error,
            'We could not queue that follow-up question right now.',
          ),
        },
      }))
    }
  }

  function handleInjectTextChange(matchId: number, value: string) {
    setPanels((current) => ({
      ...current,
      [matchId]: {
        ...current[matchId],
        injectText: value,
        injectError: null,
      },
    }))
  }

  function handleEndInterview(matchId: number) {
    setPanels((current) => ({
      ...current,
      [matchId]: {
        ...current[matchId],
        endError:
          'The current backend does not expose a recruiter end-interview endpoint yet, so this control cannot terminate the live session from client alone.',
      },
    }))
  }

  async function handleOpenCompare() {
    if (!compareRoleId) {
      setCompareError('Choose a specific role to compare candidates for that role.')
      setIsCompareOpen(true)
      return
    }

    setIsCompareOpen(true)
    setIsCompareLoading(true)
    setCompareError(null)

    try {
      const response = await fetchComparison(compareRoleId)
      setComparison(response)
    } catch (error) {
      setComparison(null)
      setCompareError(
        getErrorMessage(error, 'We could not load the candidate comparison panel right now.'),
      )
    } finally {
      setIsCompareLoading(false)
    }
  }

  return (
    <section className="space-y-6">
      <div className="rounded-[2rem] border border-border bg-surfaceAlt/90 p-6 shadow-panel sm:p-8">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-end xl:justify-between">
          <div className="max-w-3xl">
            <p className="type-kicker">Recruiter mission control</p>
            <h2 className="type-display-page mt-4">
              Monitor live interviews, catch weak signals early, and compare candidates without losing the thread.
            </h2>
            <p className="type-body mt-4 max-w-2xl">
              This dashboard follows the current Pomelo recruiter flow: active interviews come from the live recruiter API, transcripts stream in real time, and recruiter actions stay scoped per match.
            </p>
          </div>

          <div className="flex w-full flex-col gap-3 sm:flex-row xl:w-auto">
            <label className="flex min-w-[240px] flex-col gap-2">
              <span className="type-label">Role filter</span>
              <select
                value={selectedRoleId}
                onChange={(event) => {
                  setSelectedRoleId(event.target.value)
                  setCompareError(null)
                }}
                className="font-ui rounded-2xl border border-border bg-surface px-4 py-3 text-sm text-textPrimary outline-none transition focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20"
              >
                <option value="all">All active roles</option>
                {roleOptions.map((role) => (
                  <option key={role.id} value={role.id}>
                    {role.label} ({role.count})
                  </option>
                ))}
              </select>
            </label>

            <button
              type="button"
              onClick={() => void handleOpenCompare()}
              className="font-ui inline-flex items-center justify-center rounded-full border border-navButtonActive bg-navButtonActive px-5 py-3 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover"
            >
              Compare Candidates
            </button>
          </div>
        </div>
      </div>

      {loadError ? (
        <div className="rounded-[1.75rem] border border-error/30 bg-error/10 px-5 py-4 text-sm text-textPrimary">
          {loadError}
        </div>
      ) : null}

      {isLoading ? (
        <div className="rounded-[2rem] border border-border bg-surface p-10 text-center shadow-panel">
          <p className="type-kicker">Loading dashboard</p>
          <h3 className="type-display-section mt-4">
            Pulling active interviews and opening live recruiter streams.
          </h3>
        </div>
      ) : visiblePanels.length ? (
        <div className="grid gap-5 xl:grid-cols-2">
          {visiblePanels.map((panel) => {
            const summaryScore = formatWeightedScore(panel.summary?.scores_weighted)

            return (
              <article
                key={panel.interview.match_id}
                className={[
                  'relative overflow-hidden rounded-[1.85rem] border border-border bg-surface p-5 shadow-panel transition',
                  panel.completed ? 'grayscale-[0.18] opacity-85' : '',
                ].join(' ')}
              >
                <div className="flex flex-col gap-5">
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <p className="type-meta">Match #{panel.interview.match_id}</p>
                      <h3 className="mt-2 font-ui text-xl font-semibold text-textPrimary">
                        {panel.interview.candidate_name}
                      </h3>
                      <p className="type-body mt-2 text-sm leading-6">
                        {panel.interview.role_title}
                      </p>
                    </div>

                    <div className="flex shrink-0 flex-col items-end gap-2">
                      <span className="rounded-full border border-accentSecondary/40 bg-accentSecondary/15 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-textPrimary">
                        {formatProgress(panel.progressCurrent, panel.progressTotal)}
                      </span>
                      <span className="type-meta">{formatTimestamp(panel.interview.matched_at)}</span>
                    </div>
                  </div>

                  <div className="grid gap-4 lg:grid-cols-[140px_minmax(0,1fr)]">
                    <div className="space-y-3">
                      <div className="overflow-hidden rounded-[1.4rem] border border-border bg-surfaceAlt">
                        {panel.frameSrc ? (
                          <img
                            src={panel.frameSrc}
                            alt={`${panel.interview.candidate_name} live frame`}
                            className="aspect-[4/5] w-full object-cover"
                          />
                        ) : (
                          <div className="flex aspect-[4/5] items-center justify-center px-4 text-center">
                            <div>
                              <p className="font-ui text-sm font-semibold text-textPrimary">
                                Frame preview
                              </p>
                              <p className="mt-2 text-xs leading-5 text-textSecondary">
                                Waiting for the next camera frame from the live interview stream.
                              </p>
                            </div>
                          </div>
                        )}
                      </div>

                      <div className="rounded-[1.2rem] border border-border bg-background px-4 py-3">
                        <p className="type-meta">Top skills</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {panel.interview.top_skills.length ? (
                            panel.interview.top_skills.map((skill) => (
                              <span
                                key={`${panel.interview.match_id}-${skill}`}
                                className="type-badge rounded-full border border-border bg-surfaceAlt px-3 py-1.5 text-textPrimary"
                              >
                                {skill}
                              </span>
                            ))
                          ) : (
                            <span className="type-meta">No skills surfaced yet.</span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-4">
                      {panel.alerts.map((alert, index) => (
                        <div
                          key={`${panel.interview.match_id}-alert-${index}`}
                          className="rounded-[1.1rem] border border-error/35 bg-error/12 px-4 py-3 text-sm font-medium text-textPrimary"
                        >
                          {alert}
                        </div>
                      ))}

                      {panel.streamError ? (
                        <div className="rounded-[1.1rem] border border-warning/35 bg-warning/16 px-4 py-3 text-sm text-textPrimary">
                          {panel.streamError}
                        </div>
                      ) : null}

                      {panel.endError ? (
                        <div className="rounded-[1.1rem] border border-warning/35 bg-warning/16 px-4 py-3 text-sm text-textPrimary">
                          {panel.endError}
                        </div>
                      ) : null}

                      <div className="overflow-hidden rounded-[1.4rem] border border-[#332c28] bg-[#2c2522] shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
                        <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
                          <p className="font-ui text-sm font-semibold uppercase tracking-[0.18em] text-[#dbc8bf]">
                            Live transcript
                          </p>
                          <span className="font-ui text-xs font-medium uppercase tracking-[0.16em] text-[#a79991]">
                            Monospace feed
                          </span>
                        </div>

                        <div
                          ref={(node) => {
                            transcriptRefs.current[panel.interview.match_id] = node
                          }}
                          className="h-[260px] space-y-3 overflow-y-auto px-4 py-4 font-mono text-[13px] leading-6"
                        >
                          {panel.transcript.length ? (
                            panel.transcript.map((item) => (
                              <div
                                key={item.id}
                                className={[
                                  'rounded-xl border px-3 py-2.5',
                                  item.flagged
                                    ? 'border-l-4 border-l-warning'
                                    : 'border-l border-l-transparent',
                                  item.role === 'answer'
                                    ? 'border-white/10 bg-white/8 text-white'
                                    : item.role === 'score'
                                      ? 'border-accentSecondary/20 bg-[#211c19] text-[#e9dad0]'
                                      : 'border-white/8 bg-white/4 text-[#c9bbb4]',
                                ].join(' ')}
                              >
                                <div className="flex items-start justify-between gap-3">
                                  <span className="uppercase tracking-[0.16em] text-[11px] text-[#ab9b92]">
                                    {item.role === 'answer'
                                      ? 'Candidate'
                                      : item.role === 'follow_up'
                                        ? 'Injected'
                                        : item.role === 'score'
                                          ? 'Grade'
                                          : 'AI'}
                                  </span>
                                  {typeof item.score === 'number' ? (
                                    <span
                                      className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${getScoreBadgeClasses(
                                        item.score,
                                      )}`}
                                    >
                                      {formatPercent(item.score)}
                                    </span>
                                  ) : null}
                                </div>
                                <p className="mt-2 whitespace-pre-wrap">{item.text}</p>
                                {item.recruiterHint ? (
                                  <p className="mt-2 text-[12px] text-[#b9aaa1]">
                                    Hint: {item.recruiterHint}
                                  </p>
                                ) : null}
                              </div>
                            ))
                          ) : (
                            <div className="rounded-xl border border-white/8 bg-white/4 px-4 py-5 text-[#b9aaa1]">
                              Waiting for the first transcript event from this interview.
                            </div>
                          )}
                        </div>
                      </div>

                      <form
                        onSubmit={(event) => void handleInjectQuestion(panel.interview.match_id, event)}
                        className="rounded-[1.4rem] border border-border bg-surfaceAlt/80 p-4"
                      >
                        <label className="type-label" htmlFor={`inject-${panel.interview.match_id}`}>
                          Inject Question
                        </label>
                        <div className="mt-3 flex flex-col gap-3 sm:flex-row">
                          <input
                            id={`inject-${panel.interview.match_id}`}
                            type="text"
                            value={panel.injectText}
                            onChange={(event) =>
                              handleInjectTextChange(panel.interview.match_id, event.target.value)
                            }
                            placeholder="Ask for evidence, specifics, or a follow-up example."
                            className="font-ui flex-1 rounded-2xl border border-border bg-surface px-4 py-3 text-sm text-textPrimary outline-none transition placeholder:text-textSecondary/75 focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20"
                          />
                          <button
                            type="submit"
                            disabled={panel.injectPending}
                            className="font-ui inline-flex items-center justify-center rounded-full border border-navButtonActive bg-navButtonActive px-5 py-3 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover disabled:cursor-not-allowed disabled:opacity-70"
                          >
                            {panel.injectPending ? 'Sending...' : 'Inject Question'}
                          </button>
                        </div>
                        {panel.injectError ? (
                          <p className="mt-3 text-sm text-error">{panel.injectError}</p>
                        ) : null}
                      </form>

                      <button
                        type="button"
                        onClick={() => handleEndInterview(panel.interview.match_id)}
                        className="font-ui inline-flex items-center justify-center rounded-full border border-error/35 bg-error/12 px-5 py-3 text-sm font-semibold text-textPrimary transition hover:bg-error/18"
                      >
                        End Interview
                      </button>
                    </div>
                  </div>
                </div>

                {panel.completed ? (
                  <div className="absolute inset-0 flex items-center justify-center bg-surface/78 p-5 backdrop-blur-[2px]">
                    <div className="w-full max-w-md rounded-[1.5rem] border border-border bg-surface px-6 py-6 text-center shadow-panel">
                      <p className="type-kicker">Interview complete</p>
                      <h4 className="font-display mt-4 text-3xl font-semibold tracking-[-0.01em] text-textPrimary">
                        {panel.summary?.verdict ?? 'Ready for review'}
                      </h4>
                      {panel.summary?.one_liner ? (
                        <p className="type-body mt-4 text-sm leading-7 text-textPrimary">
                          {panel.summary.one_liner}
                        </p>
                      ) : null}
                      <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
                        {summaryScore ? (
                          <span className="type-badge rounded-full border border-success/35 bg-success/15 px-3 py-1.5 text-textPrimary">
                            {summaryScore}
                          </span>
                        ) : null}
                        {panel.summary?.confidence != null ? (
                          <span className="type-badge rounded-full border border-info/35 bg-info/16 px-3 py-1.5 text-textPrimary">
                            {Math.round(panel.summary.confidence * 100)}% confidence
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>
                ) : null}
              </article>
            )
          })}
        </div>
      ) : (
        <div className="rounded-[2rem] border border-border bg-surface p-10 shadow-panel">
          <p className="type-kicker">No live interviews</p>
          <h3 className="type-display-section mt-4">
            There are no active interviews in the current recruiter stream.
          </h3>
          <p className="type-body mt-4 max-w-3xl">
            Once a recruiter-created match enters the interviewing state, it will appear here with transcript updates, grading signals, candidate frames, and comparison support.
          </p>
        </div>
      )}

      <div
        className={[
          'fixed inset-y-0 right-0 z-40 w-full max-w-xl border-l border-border bg-surface/96 shadow-[0_24px_80px_rgba(139,111,99,0.18)] backdrop-blur transition-transform duration-300',
          isCompareOpen ? 'translate-x-0' : 'translate-x-full',
        ].join(' ')}
      >
        <div className="flex h-full flex-col">
          <div className="flex items-start justify-between border-b border-border px-6 py-5">
            <div>
              <p className="type-kicker">Candidate comparison</p>
              <h3 className="type-display-section mt-3">
                Side-by-side shortlist guidance
              </h3>
            </div>
            <button
              type="button"
              onClick={() => setIsCompareOpen(false)}
              className="font-ui rounded-full border border-border bg-surfaceAlt px-4 py-2 text-sm font-semibold text-textPrimary transition hover:border-accentSecondary hover:bg-accentSecondary/12"
            >
              Close
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-6 py-6">
            {isCompareLoading ? (
              <div className="rounded-[1.5rem] border border-border bg-surfaceAlt px-5 py-5">
                <p className="type-meta">Loading comparison data...</p>
              </div>
            ) : compareError ? (
              <div className="rounded-[1.5rem] border border-error/30 bg-error/10 px-5 py-5 text-sm text-textPrimary">
                {compareError}
              </div>
            ) : comparison ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {[...comparison.advance, ...comparison.reject].map((candidate, index) => {
                  const isRecommended =
                    comparison.advance.length > 0 &&
                    candidate.candidate_id === comparison.advance[0].candidate_id

                  return (
                    <article
                      key={`${candidate.match_id}-${candidate.candidate_id}-${index}`}
                      className={[
                        'rounded-[1.5rem] border bg-surfaceAlt/75 p-5',
                        isRecommended
                          ? 'border-success shadow-[0_18px_45px_rgba(127,163,122,0.16)]'
                          : 'border-border',
                      ].join(' ')}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="type-meta">Rank #{candidate.rank ?? index + 1}</p>
                          <h4 className="mt-2 font-ui text-lg font-semibold text-textPrimary">
                            {candidate.name}
                          </h4>
                        </div>
                        <span
                          className={`type-badge rounded-full border px-3 py-1.5 ${
                            isRecommended
                              ? 'border-success/35 bg-success/15 text-textPrimary'
                              : 'border-border bg-surface text-textPrimary'
                          }`}
                        >
                          {isRecommended ? 'Recommended' : candidate.recommendation ?? 'Review'}
                        </span>
                      </div>

                      <div className="mt-5 grid gap-3 sm:grid-cols-2">
                        <div className="rounded-2xl border border-border bg-surface px-4 py-3">
                          <p className="type-meta">Resume</p>
                          <p className="type-stat mt-2">
                            {formatPercentScore(candidate.resume_score_pct)}
                          </p>
                        </div>
                        <div className="rounded-2xl border border-border bg-surface px-4 py-3">
                          <p className="type-meta">Interview</p>
                          <p className="type-stat mt-2">
                            {formatPercentScore(candidate.interview_score_pct)}
                          </p>
                        </div>
                      </div>

                      <div className="mt-4 rounded-2xl border border-border bg-surface px-4 py-3">
                        <p className="type-meta">Composite</p>
                        <p className="type-stat mt-2">
                          {Math.round(candidate.total_score * 100)}%
                        </p>
                      </div>

                      <div className="mt-4 flex flex-wrap gap-2">
                        {candidate.top_skills.map((skill) => (
                          <span
                            key={`${candidate.candidate_id}-${skill}`}
                            className="type-badge rounded-full border border-border bg-surface px-3 py-1.5 text-textPrimary"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    </article>
                  )
                })}
              </div>
            ) : (
              <div className="rounded-[1.5rem] border border-border bg-surfaceAlt px-5 py-5">
                <p className="type-meta">
                  Choose a role and open comparison to review completed candidates side by side.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {isCompareOpen ? (
        <button
          type="button"
          aria-label="Close comparison panel"
          onClick={() => setIsCompareOpen(false)}
          className="fixed inset-0 z-30 bg-textPrimary/12 backdrop-blur-[1px]"
        />
      ) : null}
    </section>
  )
}
