import type { ChangeEvent, FormEvent } from 'react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../lib/api'
import { useAuth } from '../contexts/auth-context'

const MIN_QUESTIONS_GUIDANCE = 6

// ── existing types ─────────────────────────────────────────────────────────
type RecruiterRole = {
  role_id: number
  company_id: number
  title: string
  description: string
  location?: string | null
  is_remote: boolean
  min_score: number
  max_score: number
  keywords: string[]
  questions: string[]
  created_at: string
}

type CreateRolePayload = {
  company_id: number
  title: string
  description: string
  min_score: number
  max_score: number
  keywords: string[]
  questions: string[]
}

type RoleFormState = {
  title: string
  description: string
  hiddenKeywords: string
  minScore: string
  maxScore: string
  questions: string[]
}

type RoleFormErrors = {
  title?: string
  description?: string
  minScore?: string
  maxScore?: string
  questions?: string
  form?: string
}

type RoleFormValidationResult =
  | { errors: RoleFormErrors }
  | { payload: Omit<CreateRolePayload, 'company_id'> }

// ── new types for candidate queue ──────────────────────────────────────────
type QueuedCandidate = {
  candidate_id: number
  name: string
  email: string
  resume_score: number
  resume_score_pct: number
  summary: string | null
  top_skills: string[]
  swiped_at: string
  keyword_score: number | null
  keyword_reasoning: string | null
  keyword_approved: boolean | null
}

type KeywordResult = {
  keyword_score: number
  reasoning: string
  approve_for_interview: boolean
}

type SwipeOutcome = {
  matched: boolean
  match_id?: number
}

type CandidateRowState = {
  keywordLoading: boolean
  keywordError: string | null
  keyword: KeywordResult | null
  swipeLoading: boolean
  swipeError: string | null
  swipeOutcome: SwipeOutcome | null
  swipeDirection: 'like' | 'pass' | null
}

// ── helpers ────────────────────────────────────────────────────────────────
function createDefaultRoleForm(): RoleFormState {
  return {
    title: '',
    description: '',
    hiddenKeywords: '',
    minScore: '0.4',
    maxScore: '1',
    questions: Array.from({ length: MIN_QUESTIONS_GUIDANCE }, () => ''),
  }
}

function parseKeywords(value: string) {
  return value
    .split(/\n|,/)
    .map((k) => k.trim())
    .filter(Boolean)
}

function normalizeQuestions(questions: string[]) {
  return questions.map((q) => q.trim()).filter(Boolean)
}

function formatPercent(value: number) {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`
}

function formatPct(value: number) {
  return `${Math.round(Math.max(0, Math.min(100, value)))}%`
}

function formatDate(value: string) {
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime())
    ? 'Recently'
    : new Intl.DateTimeFormat(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      }).format(parsed)
}

function getErrorDetail(error: unknown, fallback: string) {
  if (!(error instanceof Error)) return fallback
  const detail = error.message.match(/status \d+(?::\s*)(.*)$/)?.[1]?.trim()
  return detail || fallback
}

function getRoleErrorMessage(error: unknown) {
  return getErrorDetail(error, 'Could not load roles right now.')
}

function getResumeScoreBadgeClasses(pct: number) {
  if (pct >= 70) return 'border-success/30 bg-success/15 text-textPrimary'
  if (pct >= 40) return 'border-warning/35 bg-warning/18 text-textPrimary'
  return 'border-error/30 bg-error/12 text-error'
}

function buildInitialCandidateState(candidate: QueuedCandidate): CandidateRowState {
  return {
    keywordLoading: false,
    keywordError: null,
    keyword:
      candidate.keyword_score != null
        ? {
            keyword_score: candidate.keyword_score,
            reasoning: candidate.keyword_reasoning ?? '',
            approve_for_interview: candidate.keyword_approved ?? false,
          }
        : null,
    swipeLoading: false,
    swipeError: null,
    swipeOutcome: null,
    swipeDirection: null,
  }
}

// ── API calls ──────────────────────────────────────────────────────────────
async function fetchRecruiterRoles(companyId: number) {
  return apiFetch<RecruiterRole[]>(`/api/recruiter/roles?company_id=${companyId}`)
}

async function createRecruiterRole(payload: CreateRolePayload) {
  return apiFetch<RecruiterRole>('/api/recruiter/roles', {
    method: 'POST',
    body: payload,
  })
}

async function fetchRoleCandidates(roleId: number) {
  return apiFetch<QueuedCandidate[]>(`/api/recruiter/roles/${roleId}/candidates`)
}

async function runKeywordFilter(roleId: number, candidateId: number) {
  return apiFetch<{
    candidate_id: number
    role_id: number
    keyword_score: number
    reasoning: string
    approve_for_interview: boolean
  }>(`/api/recruiter/roles/${roleId}/candidates/${candidateId}/keyword-filter`, {
    method: 'POST',
  })
}

async function recruiterSwipe(
  roleId: number,
  candidateId: number,
  direction: 'like' | 'pass',
) {
  return apiFetch<SwipeOutcome>(
    `/api/recruiter/roles/${roleId}/candidates/${candidateId}/swipe`,
    { method: 'POST', body: { direction } },
  )
}

// ── form validation ────────────────────────────────────────────────────────
function validateRoleForm(form: RoleFormState): RoleFormValidationResult {
  const errors: RoleFormErrors = {}
  const minScore = Number.parseFloat(form.minScore)
  const maxScore = Number.parseFloat(form.maxScore)
  const questions = normalizeQuestions(form.questions)

  if (!form.title.trim()) errors.title = 'Role title is required.'
  if (!form.description.trim()) errors.description = 'Role description is required.'

  if (Number.isNaN(minScore) || minScore < 0 || minScore > 1) {
    errors.minScore = 'Min score must be between 0.0 and 1.0.'
  }
  if (Number.isNaN(maxScore) || maxScore < 0 || maxScore > 1) {
    errors.maxScore = 'Max score must be between 0.0 and 1.0.'
  }
  if (!errors.minScore && !errors.maxScore && minScore > maxScore) {
    errors.maxScore = 'Max score must be ≥ min score.'
  }
  if (questions.length < MIN_QUESTIONS_GUIDANCE) {
    errors.questions = `Add at least ${MIN_QUESTIONS_GUIDANCE} interview questions.`
  }

  if (Object.keys(errors).length > 0) return { errors }

  return {
    payload: {
      title: form.title.trim(),
      description: form.description.trim(),
      min_score: minScore,
      max_score: maxScore,
      keywords: parseKeywords(form.hiddenKeywords),
      questions,
    },
  }
}

// ── component ──────────────────────────────────────────────────────────────
export function RecruiterRolesPage() {
  const { session } = useAuth()
  const companyId = session?.company_id ?? null

  // Role list state
  const [roles, setRoles] = useState<RecruiterRole[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [isCreatePanelOpen, setIsCreatePanelOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [form, setForm] = useState<RoleFormState>(() => createDefaultRoleForm())
  const [errors, setErrors] = useState<RoleFormErrors>({})

  // Candidate queue state
  const [selectedRoleId, setSelectedRoleId] = useState<number | null>(null)
  const [queueCandidates, setQueueCandidates] = useState<QueuedCandidate[]>([])
  const [queueLoading, setQueueLoading] = useState(false)
  const [queueError, setQueueError] = useState<string | null>(null)
  const [candidateStates, setCandidateStates] = useState<
    Record<number, CandidateRowState>
  >({})
  const queueRef = useRef<HTMLDivElement>(null)

  const normalizedQuestionCount = useMemo(
    () => normalizeQuestions(form.questions).length,
    [form.questions],
  )

  const selectedRole = useMemo(
    () => roles.find((r) => r.role_id === selectedRoleId) ?? null,
    [roles, selectedRoleId],
  )

  const pendingCandidates = useMemo(
    () =>
      queueCandidates.filter(
        (c) => !candidateStates[c.candidate_id]?.swipeOutcome,
      ),
    [queueCandidates, candidateStates],
  )

  const reviewedCandidates = useMemo(
    () =>
      queueCandidates.filter(
        (c) => !!candidateStates[c.candidate_id]?.swipeOutcome,
      ),
    [queueCandidates, candidateStates],
  )

  // ── load roles ────────────────────────────────────────────────
  async function loadRoles(id: number) {
    setIsLoading(true)
    setLoadError(null)
    try {
      setRoles(await fetchRecruiterRoles(id))
    } catch (error) {
      setRoles([])
      setLoadError(getRoleErrorMessage(error))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (companyId == null) {
      setIsLoading(false)
      setLoadError('No company associated with your session.')
      return
    }
    void loadRoles(companyId)
  }, [companyId])

  // ── load candidate queue ──────────────────────────────────────
  async function loadQueue(roleId: number) {
    setQueueLoading(true)
    setQueueError(null)
    try {
      const candidates = await fetchRoleCandidates(roleId)
      setQueueCandidates(candidates)
      const states: Record<number, CandidateRowState> = {}
      for (const c of candidates) {
        states[c.candidate_id] = buildInitialCandidateState(c)
      }
      setCandidateStates(states)
    } catch (error) {
      setQueueCandidates([])
      setCandidateStates({})
      setQueueError(
        getErrorDetail(error, 'Could not load the candidate queue for this role.'),
      )
    } finally {
      setQueueLoading(false)
    }
  }

  useEffect(() => {
    if (selectedRoleId == null) {
      setQueueCandidates([])
      setCandidateStates({})
      setQueueError(null)
      return
    }
    void loadQueue(selectedRoleId)
    window.setTimeout(() => {
      queueRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 80)
  }, [selectedRoleId])

  // ── form helpers ──────────────────────────────────────────────
  function updateFormField<K extends keyof RoleFormState>(
    key: K,
    value: RoleFormState[K],
  ) {
    setForm((c) => ({ ...c, [key]: value }))
    setErrors((c) => ({ ...c, form: undefined }))
    setSuccessMessage(null)
  }

  function handleQuestionChange(
    index: number,
    event: ChangeEvent<HTMLInputElement>,
  ) {
    const next = [...form.questions]
    next[index] = event.target.value
    updateFormField('questions', next)
    setErrors((c) => ({ ...c, questions: undefined, form: undefined }))
  }

  async function handleCreateRole(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSuccessMessage(null)

    if (companyId == null) {
      setErrors({ form: 'No company session found. Please sign in again.' })
      return
    }

    const result = validateRoleForm(form)
    if ('errors' in result) {
      setErrors(result.errors)
      return
    }

    setIsSubmitting(true)
    setErrors({})

    try {
      const created = await createRecruiterRole({
        company_id: companyId,
        ...result.payload,
      })
      setForm(createDefaultRoleForm())
      setIsCreatePanelOpen(false)
      setSuccessMessage(`Role "${created.title}" created.`)
      await loadRoles(companyId)
    } catch (error) {
      setErrors({ form: getRoleErrorMessage(error) })
    } finally {
      setIsSubmitting(false)
    }
  }

  // ── queue action helpers ──────────────────────────────────────
  function updateCandidateState(
    candidateId: number,
    patch: Partial<CandidateRowState>,
  ) {
    setCandidateStates((prev) => ({
      ...prev,
      [candidateId]: { ...prev[candidateId], ...patch },
    }))
  }

  async function handleKeywordScreen(candidateId: number) {
    if (selectedRoleId == null) return
    updateCandidateState(candidateId, {
      keywordLoading: true,
      keywordError: null,
    })
    try {
      const result = await runKeywordFilter(selectedRoleId, candidateId)
      updateCandidateState(candidateId, {
        keywordLoading: false,
        keyword: {
          keyword_score: result.keyword_score,
          reasoning: result.reasoning,
          approve_for_interview: result.approve_for_interview,
        },
      })
    } catch (error) {
      updateCandidateState(candidateId, {
        keywordLoading: false,
        keywordError: getErrorDetail(error, 'Keyword screening failed.'),
      })
    }
  }

  async function handleSwipe(
    candidateId: number,
    direction: 'like' | 'pass',
  ) {
    if (selectedRoleId == null) return
    updateCandidateState(candidateId, {
      swipeLoading: true,
      swipeError: null,
    })
    try {
      const result = await recruiterSwipe(selectedRoleId, candidateId, direction)
      updateCandidateState(candidateId, {
        swipeLoading: false,
        swipeOutcome: result,
        swipeDirection: direction,
      })
    } catch (error) {
      updateCandidateState(candidateId, {
        swipeLoading: false,
        swipeError: getErrorDetail(
          error,
          'Could not record your decision. Try again.',
        ),
      })
    }
  }

  // ── render ────────────────────────────────────────────────────
  return (
    <section className="space-y-8">
      {/* ── Header ── */}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(280px,0.95fr)]">
        <div className="rounded-[2rem] border border-border bg-surfaceAlt p-8 shadow-panel">
          <p className="type-kicker">Recruiter roles</p>
          <h2 className="type-display-hero mt-5 max-w-3xl">
            Configure role criteria, keywords, and interview questions.
          </h2>
          <p className="type-body mt-5 max-w-2xl">
            Roles load automatically from your company account. Hidden keywords
            drive candidate matching. Score range determines which candidates see
            the role in their feed.
          </p>

          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            <div className="rounded-3xl border border-border bg-surface p-5">
              <p className="type-meta">Company</p>
              <p className="type-stat mt-3">
                {companyId != null ? `#${companyId}` : '—'}
              </p>
            </div>
            <div className="rounded-3xl border border-border bg-surface p-5">
              <p className="type-meta">Active roles</p>
              <p className="type-stat mt-3">{roles.length}</p>
            </div>
            <div className="rounded-3xl border border-border bg-surface p-5">
              <p className="type-meta">Min questions</p>
              <p className="type-stat mt-3">{MIN_QUESTIONS_GUIDANCE}</p>
            </div>
          </div>
        </div>

        <div className="flex flex-col justify-center rounded-[2rem] border border-border bg-surface p-8 shadow-panel">
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => {
                setIsCreatePanelOpen((c) => !c)
                setErrors({})
                setSuccessMessage(null)
              }}
              className="inline-flex w-full items-center justify-center rounded-full border border-navButtonActive bg-navButtonActive px-5 py-3 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover"
            >
              {isCreatePanelOpen ? 'Cancel' : 'Create new role'}
            </button>
            <button
              type="button"
              onClick={() => companyId != null && void loadRoles(companyId)}
              disabled={isLoading || companyId == null}
              className="inline-flex w-full items-center justify-center rounded-full border border-border bg-surfaceAlt px-5 py-3 text-sm font-semibold text-textPrimary transition hover:border-accentSecondary hover:bg-accentSecondary/15 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? 'Refreshing…' : 'Refresh roles'}
            </button>
            <Link
              to={
                selectedRoleId != null
                  ? `/recruiter/dashboard?roleId=${selectedRoleId}`
                  : '/recruiter/dashboard'
              }
              className="inline-flex w-full items-center justify-center rounded-full border border-border bg-surfaceAlt px-5 py-3 text-sm font-semibold text-textPrimary transition hover:border-accentSecondary hover:bg-accentSecondary/15"
            >
              Live monitor →
            </Link>
          </div>

          {loadError ? (
            <div className="mt-4 rounded-3xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">
              {loadError}
            </div>
          ) : null}

          {successMessage ? (
            <div className="mt-4 rounded-3xl border border-success/30 bg-success/12 px-4 py-3 text-sm text-textPrimary">
              {successMessage}
            </div>
          ) : null}
        </div>
      </div>

      {/* ── Create role panel ── */}
      {isCreatePanelOpen ? (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,0.72fr)_minmax(360px,0.92fr)]">
          <div className="rounded-[2rem] border border-border bg-surfaceAlt p-8 shadow-panel">
            <p className="text-sm font-medium uppercase tracking-[0.32em] text-textSecondary">
              Role creation guide
            </p>
            <h3 className="mt-4 text-3xl font-semibold tracking-tight text-textPrimary">
              Keep role definitions tight and high-signal.
            </h3>
            <div className="mt-6 space-y-4 text-sm leading-7 text-textSecondary">
              <p>
                Hidden keywords drive backend matching — use them for frameworks,
                domain depth, or team-specific signals you care about most.
              </p>
              <p>
                Score bounds use a normalized <code>0.0–1.0</code> format. A
                range of <code>0.65–1.0</code> targets candidates at 65%+ fit.
              </p>
              <p>
                Add at least {MIN_QUESTIONS_GUIDANCE} interview questions as
                plain-text prompts. The AI uses these as the role-specific
                question foundation.
              </p>
            </div>
          </div>

          <form
            onSubmit={(e) => void handleCreateRole(e)}
            className="rounded-[2rem] border border-border bg-surface p-8 shadow-panel"
          >
            <div className="grid gap-6">
              <div className="space-y-2">
                <label
                  className="text-sm font-medium text-textPrimary"
                  htmlFor="role-title"
                >
                  Role title
                </label>
                <input
                  id="role-title"
                  type="text"
                  value={form.title}
                  onChange={(e) => {
                    updateFormField('title', e.target.value)
                    setErrors((c) => ({ ...c, title: undefined }))
                  }}
                  disabled={isSubmitting}
                  className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-base text-textPrimary outline-none transition placeholder:text-textSecondary/75 focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20 disabled:cursor-not-allowed disabled:opacity-70"
                  placeholder="Founding Product Engineer"
                />
                {errors.title ? (
                  <p className="text-sm text-error">{errors.title}</p>
                ) : null}
              </div>

              <div className="space-y-2">
                <label
                  className="text-sm font-medium text-textPrimary"
                  htmlFor="role-description"
                >
                  Description
                </label>
                <textarea
                  id="role-description"
                  rows={5}
                  value={form.description}
                  onChange={(e) => {
                    updateFormField('description', e.target.value)
                    setErrors((c) => ({ ...c, description: undefined }))
                  }}
                  disabled={isSubmitting}
                  className="w-full rounded-[1.5rem] border border-border bg-background px-4 py-3 text-base text-textPrimary outline-none transition placeholder:text-textSecondary/75 focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20 disabled:cursor-not-allowed disabled:opacity-70"
                  placeholder="Describe the role scope, team context, and what strong candidates should have done before."
                />
                {errors.description ? (
                  <p className="text-sm text-error">{errors.description}</p>
                ) : null}
              </div>

              <div className="space-y-2">
                <label
                  className="text-sm font-medium text-textPrimary"
                  htmlFor="role-keywords"
                >
                  Hidden keywords
                </label>
                <textarea
                  id="role-keywords"
                  rows={4}
                  value={form.hiddenKeywords}
                  onChange={(e) => updateFormField('hiddenKeywords', e.target.value)}
                  disabled={isSubmitting}
                  className="w-full rounded-[1.5rem] border border-border bg-background px-4 py-3 text-base text-textPrimary outline-none transition placeholder:text-textSecondary/75 focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20 disabled:cursor-not-allowed disabled:opacity-70"
                  placeholder={'distributed systems\nNext.js\nfounder energy'}
                />
                <p className="text-sm leading-6 text-textSecondary">
                  Commas or new lines. Hidden from candidates.
                </p>
              </div>

              <div className="grid gap-6 sm:grid-cols-2">
                <div className="space-y-2">
                  <label
                    className="text-sm font-medium text-textPrimary"
                    htmlFor="role-min-score"
                  >
                    Min score (0.0–1.0)
                  </label>
                  <input
                    id="role-min-score"
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={form.minScore}
                    onChange={(e) => {
                      updateFormField('minScore', e.target.value)
                      setErrors((c) => ({
                        ...c,
                        minScore: undefined,
                        maxScore: undefined,
                      }))
                    }}
                    disabled={isSubmitting}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-base text-textPrimary outline-none transition focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20 disabled:cursor-not-allowed disabled:opacity-70"
                    placeholder="0.4"
                  />
                  <p className="text-sm text-textSecondary">
                    {formatPercent(Number(form.minScore) || 0)} fit minimum
                  </p>
                  {errors.minScore ? (
                    <p className="text-sm text-error">{errors.minScore}</p>
                  ) : null}
                </div>

                <div className="space-y-2">
                  <label
                    className="text-sm font-medium text-textPrimary"
                    htmlFor="role-max-score"
                  >
                    Max score (0.0–1.0)
                  </label>
                  <input
                    id="role-max-score"
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={form.maxScore}
                    onChange={(e) => {
                      updateFormField('maxScore', e.target.value)
                      setErrors((c) => ({
                        ...c,
                        minScore: undefined,
                        maxScore: undefined,
                      }))
                    }}
                    disabled={isSubmitting}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-base text-textPrimary outline-none transition focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20 disabled:cursor-not-allowed disabled:opacity-70"
                    placeholder="1.0"
                  />
                  <p className="text-sm text-textSecondary">
                    {formatPercent(Number(form.maxScore) || 0)} fit maximum
                  </p>
                  {errors.maxScore ? (
                    <p className="text-sm text-error">{errors.maxScore}</p>
                  ) : null}
                </div>
              </div>

              {/* Questions */}
              <div className="rounded-[1.75rem] border border-border bg-surfaceAlt/65 p-5">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm font-medium uppercase tracking-[0.24em] text-textSecondary">
                      Interview questions
                    </p>
                    <p className="mt-2 text-sm leading-6 text-textSecondary">
                      {normalizedQuestionCount}/{MIN_QUESTIONS_GUIDANCE} minimum
                      ready
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      updateFormField('questions', [...form.questions, ''])
                    }
                    disabled={isSubmitting}
                    className="inline-flex items-center justify-center rounded-full border border-border bg-surface px-4 py-2 text-sm font-semibold text-textPrimary transition hover:border-accentSecondary hover:bg-accentSecondary/15 disabled:opacity-70"
                  >
                    Add question
                  </button>
                </div>

                <div className="mt-5 space-y-3">
                  {form.questions.map((question, index) => (
                    <div
                      key={`q-${index}`}
                      className="flex flex-col gap-3 rounded-[1.5rem] border border-border bg-surface p-4 sm:flex-row sm:items-start"
                    >
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accentHighlight text-sm font-semibold text-textPrimary">
                        {index + 1}
                      </div>
                      <input
                        type="text"
                        value={question}
                        onChange={(e) => handleQuestionChange(index, e)}
                        disabled={isSubmitting}
                        className="flex-1 rounded-2xl border border-border bg-background px-4 py-3 text-base text-textPrimary outline-none transition focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20 disabled:opacity-70"
                        placeholder="Ask a role-specific question in plain text."
                      />
                      <button
                        type="button"
                        onClick={() =>
                          updateFormField(
                            'questions',
                            form.questions.filter((_, i) => i !== index),
                          )
                        }
                        disabled={isSubmitting || form.questions.length === 1}
                        className="inline-flex items-center justify-center rounded-full border border-border px-4 py-2 text-sm font-medium text-textSecondary transition hover:border-error/35 hover:bg-error/8 hover:text-error disabled:opacity-50"
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>

                {errors.questions ? (
                  <p className="mt-4 text-sm text-error">{errors.questions}</p>
                ) : null}
              </div>

              {errors.form ? (
                <div className="rounded-3xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">
                  {errors.form}
                </div>
              ) : null}

              <div className="flex flex-wrap gap-3">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="inline-flex items-center justify-center rounded-full border border-navButtonActive bg-navButtonActive px-6 py-3 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover disabled:opacity-70"
                >
                  {isSubmitting ? 'Creating…' : 'Create role'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setForm(createDefaultRoleForm())
                    setErrors({})
                    setSuccessMessage(null)
                  }}
                  disabled={isSubmitting}
                  className="inline-flex items-center justify-center rounded-full border border-border bg-surfaceAlt px-6 py-3 text-sm font-semibold text-textPrimary transition hover:border-accentSecondary hover:bg-accentSecondary/15 disabled:opacity-70"
                >
                  Reset
                </button>
              </div>
            </div>
          </form>
        </div>
      ) : null}

      {/* ── Role list ── */}
      <div className="space-y-4">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
          <h3 className="text-2xl font-semibold text-textPrimary">
            {isLoading
              ? 'Loading roles…'
              : roles.length
                ? `${roles.length} role${roles.length !== 1 ? 's' : ''}`
                : 'No roles yet'}
          </h3>
        </div>

        {isLoading ? (
          <div className="rounded-[2rem] border border-border bg-surface p-8 text-center shadow-panel">
            <p className="text-sm text-textSecondary">Fetching roles…</p>
          </div>
        ) : roles.length ? (
          <div className="grid gap-5 lg:grid-cols-2 2xl:grid-cols-3">
            {roles.map((role) => {
              const isSelected = selectedRoleId === role.role_id
              return (
                <article
                  key={role.role_id}
                  className={[
                    'rounded-[2rem] border bg-surface p-6 shadow-panel transition',
                    isSelected
                      ? 'border-accentPrimary/50 ring-2 ring-accentPrimary/20'
                      : 'border-border',
                  ].join(' ')}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-xs uppercase tracking-[0.28em] text-textSecondary">
                        Role #{role.role_id}
                      </p>
                      <h4 className="mt-3 text-2xl font-semibold tracking-tight text-textPrimary">
                        {role.title}
                      </h4>
                    </div>
                    <span className="rounded-full border border-accentSecondary/45 bg-accentSecondary/15 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-textPrimary">
                      {formatDate(role.created_at)}
                    </span>
                  </div>

                  <p className="mt-4 text-sm leading-7 text-textSecondary">
                    {role.description}
                  </p>

                  <div className="mt-6 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-3xl border border-border bg-surfaceAlt p-4">
                      <p className="text-sm text-textSecondary">Score range</p>
                      <p className="mt-2 text-lg font-semibold text-textPrimary">
                        {formatPercent(role.min_score)}–
                        {formatPercent(role.max_score)}
                      </p>
                    </div>
                    <div className="rounded-3xl border border-border bg-surfaceAlt p-4">
                      <p className="text-sm text-textSecondary">Questions</p>
                      <p className="mt-2 text-lg font-semibold text-textPrimary">
                        {role.questions.length} saved
                      </p>
                    </div>
                  </div>

                  {role.keywords.length > 0 ? (
                    <div className="mt-6">
                      <p className="text-sm font-medium text-textPrimary">
                        Keywords
                      </p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {role.keywords.map((kw) => (
                          <span
                            key={`${role.role_id}-${kw}`}
                            className="rounded-full border border-border bg-surfaceAlt px-3 py-1.5 text-sm font-medium text-textPrimary"
                          >
                            {kw}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  <div className="mt-6">
                    <button
                      type="button"
                      onClick={() =>
                        setSelectedRoleId(isSelected ? null : role.role_id)
                      }
                      className={[
                        'font-ui inline-flex w-full items-center justify-center rounded-full border px-5 py-2.5 text-sm font-semibold transition',
                        isSelected
                          ? 'border-border bg-surfaceAlt text-textPrimary hover:border-accentSecondary hover:bg-accentSecondary/12'
                          : 'border-navButtonActive bg-navButtonActive text-navButtonText hover:border-navButtonHover hover:bg-navButtonHover',
                      ].join(' ')}
                    >
                      {isSelected ? 'Close queue' : 'Review candidates'}
                    </button>
                  </div>
                </article>
              )
            })}
          </div>
        ) : (
          <div className="rounded-[2rem] border border-border bg-surface p-8 shadow-panel">
            <p className="text-sm font-medium uppercase tracking-[0.32em] text-textSecondary">
              No roles yet
            </p>
            <h4 className="mt-3 text-2xl font-semibold text-textPrimary">
              Create your first role to start the hiring pipeline.
            </h4>
            <p className="mt-4 max-w-3xl text-base leading-7 text-textSecondary">
              Open the create-role panel above to define keywords, score range,
              and interview questions.
            </p>
          </div>
        )}
      </div>

      {/* ── Candidate review queue ── */}
      {selectedRoleId != null && selectedRole != null ? (
        <div ref={queueRef} className="space-y-5 scroll-mt-8">
          {/* Queue header */}
          <div className="rounded-[2rem] border border-border bg-surfaceAlt/90 p-6 shadow-panel sm:p-8">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
              <div className="min-w-0">
                <p className="type-kicker">Candidate review queue</p>
                <h3 className="type-display-section mt-3 truncate">
                  {selectedRole.title}
                </h3>
                <p className="type-body mt-2 max-w-2xl">
                  Candidates who liked this role. Run a keyword screen to check
                  fit against your hidden criteria, then like or pass.
                </p>
              </div>
              <div className="flex shrink-0 gap-3">
                <button
                  type="button"
                  onClick={() => void loadQueue(selectedRoleId)}
                  disabled={queueLoading}
                  className="font-ui inline-flex items-center justify-center rounded-full border border-border bg-surface px-5 py-2.5 text-sm font-semibold text-textPrimary transition hover:border-accentSecondary hover:bg-accentSecondary/12 disabled:opacity-50"
                >
                  {queueLoading ? 'Loading…' : 'Refresh'}
                </button>
                <button
                  type="button"
                  onClick={() => setSelectedRoleId(null)}
                  className="font-ui inline-flex items-center justify-center rounded-full border border-border bg-surfaceAlt px-5 py-2.5 text-sm font-semibold text-textPrimary transition hover:border-error/35 hover:bg-error/8 hover:text-error"
                >
                  Close
                </button>
              </div>
            </div>

            {!queueLoading && !queueError ? (
              <div className="mt-6 grid grid-cols-3 gap-4 sm:grid-cols-3">
                <div className="rounded-3xl border border-border bg-surface p-4">
                  <p className="type-meta">In queue</p>
                  <p className="type-stat mt-2">{pendingCandidates.length}</p>
                </div>
                <div className="rounded-3xl border border-border bg-surface p-4">
                  <p className="type-meta">Reviewed</p>
                  <p className="type-stat mt-2">{reviewedCandidates.length}</p>
                </div>
                <div className="rounded-3xl border border-border bg-surface p-4">
                  <p className="type-meta">Matched</p>
                  <p className="type-stat mt-2">
                    {
                      reviewedCandidates.filter(
                        (c) => candidateStates[c.candidate_id]?.swipeOutcome?.matched,
                      ).length
                    }
                  </p>
                </div>
              </div>
            ) : null}
          </div>

          {/* Loading / error states */}
          {queueLoading ? (
            <div className="rounded-[2rem] border border-border bg-surface p-10 text-center shadow-panel">
              <p className="type-kicker">Loading queue</p>
              <h4 className="type-display-section mt-4">
                Fetching candidates for {selectedRole.title}…
              </h4>
            </div>
          ) : queueError ? (
            <div className="rounded-[2rem] border border-error/30 bg-error/10 p-8 shadow-panel">
              <p className="type-kicker text-error">Queue error</p>
              <p className="type-body mt-3">{queueError}</p>
            </div>
          ) : pendingCandidates.length === 0 && reviewedCandidates.length === 0 ? (
            <div className="rounded-[2rem] border border-border bg-surface p-10 shadow-panel">
              <p className="type-kicker">Empty queue</p>
              <h4 className="type-display-section mt-4">
                No candidates have liked this role yet.
              </h4>
              <p className="type-body mt-4 max-w-xl">
                Candidates will appear here after they swipe right on this role
                in their feed. Check back or refresh.
              </p>
            </div>
          ) : null}

          {/* Pending candidate cards */}
          {!queueLoading && pendingCandidates.length > 0 ? (
            <div className="space-y-4">
              <p className="type-kicker px-1">Awaiting review</p>
              {pendingCandidates.map((candidate) => {
                const cstate = candidateStates[candidate.candidate_id]
                if (!cstate) return null

                return (
                  <article
                    key={candidate.candidate_id}
                    className="rounded-[2rem] border border-border bg-surface p-6 shadow-panel"
                  >
                    {/* Candidate header */}
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <p className="type-meta">
                          Candidate #{candidate.candidate_id}
                        </p>
                        <h4 className="mt-2 font-ui text-xl font-semibold text-textPrimary">
                          {candidate.name}
                        </h4>
                        <p className="font-ui mt-1 text-sm text-textSecondary">
                          {candidate.email}
                        </p>
                      </div>
                      <div className="flex shrink-0 flex-col items-end gap-2">
                        <span
                          className={`type-badge rounded-full border px-3 py-1 ${getResumeScoreBadgeClasses(
                            candidate.resume_score_pct,
                          )}`}
                        >
                          {formatPct(candidate.resume_score_pct)} fit
                        </span>
                        <span className="type-meta">
                          Swiped {formatDate(candidate.swiped_at)}
                        </span>
                      </div>
                    </div>

                    {/* Summary */}
                    {candidate.summary ? (
                      <p
                        className="font-ui mt-4 text-sm leading-7 text-textSecondary"
                        style={{
                          display: '-webkit-box',
                          WebkitLineClamp: 3,
                          WebkitBoxOrient: 'vertical',
                          overflow: 'hidden',
                        }}
                      >
                        {candidate.summary}
                      </p>
                    ) : null}

                    {/* Top skills */}
                    {candidate.top_skills.length > 0 ? (
                      <div className="mt-4 flex flex-wrap gap-2">
                        {candidate.top_skills.map((skill) => (
                          <span
                            key={`${candidate.candidate_id}-${skill}`}
                            className="type-badge rounded-full border border-border bg-surfaceAlt px-3 py-1.5 text-textPrimary"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    ) : null}

                    {/* Keyword screening result */}
                    {cstate.keyword ? (
                      <div className="mt-5 rounded-[1.5rem] border border-border bg-surfaceAlt/80 p-4">
                        <div className="flex flex-wrap items-center gap-3">
                          <p className="font-ui text-sm font-semibold text-textPrimary">
                            Keyword screen
                          </p>
                          <span
                            className={`type-badge rounded-full border px-3 py-1 text-xs ${
                              cstate.keyword.approve_for_interview
                                ? 'border-success/35 bg-success/15 text-textPrimary'
                                : 'border-error/30 bg-error/10 text-error'
                            }`}
                          >
                            {cstate.keyword.approve_for_interview
                              ? 'Approved for interview'
                              : 'Not recommended'}
                          </span>
                          <span className="ml-auto font-ui text-sm font-semibold text-textPrimary">
                            {formatPct(cstate.keyword.keyword_score)}
                          </span>
                        </div>
                        <p className="font-ui mt-3 text-sm leading-6 text-textSecondary">
                          {cstate.keyword.reasoning}
                        </p>
                      </div>
                    ) : null}

                    {cstate.keywordError ? (
                      <p className="mt-3 text-sm text-error">
                        {cstate.keywordError}
                      </p>
                    ) : null}

                    {cstate.swipeError ? (
                      <p className="mt-3 text-sm text-error">
                        {cstate.swipeError}
                      </p>
                    ) : null}

                    {/* Actions */}
                    <div className="mt-6 flex flex-wrap items-center gap-3">
                      <button
                        type="button"
                        onClick={() =>
                          void handleKeywordScreen(candidate.candidate_id)
                        }
                        disabled={cstate.keywordLoading}
                        className="font-ui inline-flex items-center justify-center rounded-full border border-border bg-surfaceAlt px-5 py-2.5 text-sm font-semibold text-textPrimary transition hover:border-accentSecondary hover:bg-accentSecondary/12 disabled:opacity-50"
                      >
                        {cstate.keywordLoading
                          ? 'Screening…'
                          : cstate.keyword
                            ? 'Re-run screen'
                            : 'Run keyword screen'}
                      </button>

                      <div className="ml-auto flex gap-3">
                        <button
                          type="button"
                          onClick={() =>
                            void handleSwipe(candidate.candidate_id, 'pass')
                          }
                          disabled={cstate.swipeLoading}
                          className="font-ui inline-flex items-center justify-center rounded-full border border-error/30 bg-error/10 px-5 py-2.5 text-sm font-semibold text-error transition hover:bg-error/18 disabled:opacity-50"
                        >
                          {cstate.swipeLoading ? '…' : 'Pass'}
                        </button>
                        <button
                          type="button"
                          onClick={() =>
                            void handleSwipe(candidate.candidate_id, 'like')
                          }
                          disabled={cstate.swipeLoading}
                          className="font-ui inline-flex items-center justify-center rounded-full border border-success/30 bg-success/15 px-5 py-2.5 text-sm font-semibold text-success transition hover:bg-success/22 disabled:opacity-50"
                        >
                          {cstate.swipeLoading ? '…' : 'Like'}
                        </button>
                      </div>
                    </div>
                  </article>
                )
              })}
            </div>
          ) : null}

          {/* Reviewed candidates — compact rows */}
          {!queueLoading && reviewedCandidates.length > 0 ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <p className="type-kicker">Reviewed</p>
                {reviewedCandidates.some(
                  (c) => candidateStates[c.candidate_id]?.swipeOutcome?.matched,
                ) ? (
                  <Link
                    to={`/recruiter/dashboard?roleId=${selectedRoleId ?? ''}`}
                    className="font-ui text-sm font-semibold text-navButton underline-offset-2 hover:text-navButtonHover hover:underline"
                  >
                    Monitor live interviews →
                  </Link>
                ) : null}
              </div>
              {reviewedCandidates.map((candidate) => {
                const cstate = candidateStates[candidate.candidate_id]
                const outcome = cstate?.swipeOutcome
                const direction = cstate?.swipeDirection

                return (
                  <div
                    key={candidate.candidate_id}
                    className="flex flex-wrap items-center justify-between gap-3 rounded-[1.5rem] border border-border bg-surface px-5 py-4"
                  >
                    <div className="min-w-0">
                      <p className="font-ui text-sm font-semibold text-textPrimary">
                        {candidate.name}
                      </p>
                      <p className="type-meta mt-0.5 truncate">
                        {candidate.email}
                      </p>
                    </div>

                    <div className="flex shrink-0 flex-wrap items-center gap-3">
                      {outcome?.matched ? (
                        <>
                          <span className="type-badge rounded-full border border-success/35 bg-success/15 px-3 py-1 text-textPrimary">
                            Match created
                          </span>
                          <Link
                            to={`/recruiter/dashboard?roleId=${selectedRoleId}&matchId=${outcome?.match_id ?? ''}`}
                            className="font-ui text-sm font-semibold text-navButton underline-offset-2 hover:text-navButtonHover hover:underline"
                          >
                            View in dashboard →
                          </Link>
                        </>
                      ) : direction === 'like' ? (
                        <span className="type-badge rounded-full border border-info/35 bg-info/15 px-3 py-1 text-textPrimary">
                          Liked — awaiting candidate swipe
                        </span>
                      ) : (
                        <span className="type-badge rounded-full border border-border bg-surfaceAlt px-3 py-1 text-textSecondary">
                          Passed
                        </span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  )
}
