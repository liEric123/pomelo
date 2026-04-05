import type { ChangeEvent, FormEvent } from 'react'
import { useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../lib/api'

const DEFAULT_COMPANY_ID = '1'
const MIN_REQUIRED_QUESTIONS = 6

type RecruiterRole = {
  id: number
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
  companyId: string
  title: string
  description: string
  hiddenKeywords: string
  minScore: string
  maxScore: string
  questions: string[]
}

type RoleFormErrors = {
  companyId?: string
  title?: string
  description?: string
  minScore?: string
  maxScore?: string
  questions?: string
  form?: string
}

type RoleFormValidationResult =
  | { errors: RoleFormErrors }
  | { payload: CreateRolePayload }

function createDefaultRoleForm(companyId = DEFAULT_COMPANY_ID): RoleFormState {
  return {
    companyId,
    title: '',
    description: '',
    hiddenKeywords: '',
    minScore: '0.4',
    maxScore: '1',
    questions: Array.from({ length: MIN_REQUIRED_QUESTIONS }, () => ''),
  }
}

function parseKeywords(value: string) {
  return value
    .split(/\n|,/)
    .map((keyword) => keyword.trim())
    .filter(Boolean)
}

function normalizeQuestions(questions: string[]) {
  return questions.map((question) => question.trim()).filter(Boolean)
}

function formatPercent(value: number) {
  return `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`
}

function formatCreatedAt(value: string) {
  const parsed = new Date(value)

  if (Number.isNaN(parsed.getTime())) {
    return 'Recently created'
  }

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(parsed)
}

function getRoleErrorMessage(error: unknown) {
  if (!(error instanceof Error)) {
    return 'We could not load recruiter roles right now.'
  }

  const detail = error.message.match(/status \d+(?::\s*)(.*)$/)?.[1]?.trim()
  return detail || 'We could not load recruiter roles right now.'
}

async function fetchRecruiterRoles(companyId: number) {
  return apiFetch<RecruiterRole[]>(`/api/recruiter/roles?company_id=${companyId}`)
}

async function createRecruiterRole(payload: CreateRolePayload) {
  return apiFetch<RecruiterRole>('/api/recruiter/roles', {
    method: 'POST',
    body: payload,
  })
}

function validateRoleForm(form: RoleFormState): RoleFormValidationResult {
  const errors: RoleFormErrors = {}
  const companyId = Number.parseInt(form.companyId, 10)
  const minScore = Number.parseFloat(form.minScore)
  const maxScore = Number.parseFloat(form.maxScore)
  const questions = normalizeQuestions(form.questions)

  if (!form.companyId.trim() || Number.isNaN(companyId) || companyId <= 0) {
    errors.companyId = 'Enter a valid company ID.'
  }

  if (!form.title.trim()) {
    errors.title = 'Role title is required.'
  }

  if (!form.description.trim()) {
    errors.description = 'Role description is required.'
  }

  if (Number.isNaN(minScore)) {
    errors.minScore = 'Min score is required.'
  } else if (minScore < 0 || minScore > 1) {
    errors.minScore = 'Use a score between 0.0 and 1.0.'
  }

  if (Number.isNaN(maxScore)) {
    errors.maxScore = 'Max score is required.'
  } else if (maxScore < 0 || maxScore > 1) {
    errors.maxScore = 'Use a score between 0.0 and 1.0.'
  }

  if (
    !errors.minScore &&
    !errors.maxScore &&
    !Number.isNaN(minScore) &&
    !Number.isNaN(maxScore) &&
    minScore > maxScore
  ) {
    errors.maxScore = 'Max score must be greater than or equal to min score.'
  }

  if (questions.length < MIN_REQUIRED_QUESTIONS) {
    errors.questions = 'Add at least 6 plain-text questions before submitting.'
  }

  if (Object.keys(errors).length > 0) {
    return { errors }
  }

  return {
    payload: {
      company_id: companyId,
      title: form.title.trim(),
      description: form.description.trim(),
      min_score: minScore,
      max_score: maxScore,
      keywords: parseKeywords(form.hiddenKeywords),
      questions,
    } satisfies CreateRolePayload,
  }
}

export function RecruiterRolesPage() {
  const [companyFilter, setCompanyFilter] = useState(DEFAULT_COMPANY_ID)
  const [loadedCompanyId, setLoadedCompanyId] = useState<number | null>(null)
  const [roles, setRoles] = useState<RecruiterRole[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [isCreatePanelOpen, setIsCreatePanelOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [form, setForm] = useState<RoleFormState>(() => createDefaultRoleForm())
  const [errors, setErrors] = useState<RoleFormErrors>({})

  const normalizedQuestionCount = useMemo(
    () => normalizeQuestions(form.questions).length,
    [form.questions],
  )

  async function loadRolesForCompany(companyId: number) {
    setIsLoading(true)
    setLoadError(null)

    try {
      const response = await fetchRecruiterRoles(companyId)
      setRoles(response)
      setLoadedCompanyId(companyId)
      setCompanyFilter(String(companyId))
      setForm((current) => ({ ...current, companyId: String(companyId) }))
    } catch (error) {
      setRoles([])
      setLoadedCompanyId(companyId)
      setLoadError(getRoleErrorMessage(error))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadRolesForCompany(Number.parseInt(DEFAULT_COMPANY_ID, 10))
  }, [])

  function handleCompanyFilterSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSuccessMessage(null)

    const companyId = Number.parseInt(companyFilter, 10)

    if (Number.isNaN(companyId) || companyId <= 0) {
      setLoadError('Enter a valid company ID to view recruiter roles.')
      setLoadedCompanyId(null)
      setRoles([])
      return
    }

    void loadRolesForCompany(companyId)
  }

  function updateFormField<Key extends keyof RoleFormState>(
    key: Key,
    value: RoleFormState[Key],
  ) {
    setForm((current) => ({ ...current, [key]: value }))
    setErrors((current) => ({ ...current, form: undefined }))
    setSuccessMessage(null)
  }

  function handleQuestionChange(index: number, event: ChangeEvent<HTMLInputElement>) {
    const nextQuestions = [...form.questions]
    nextQuestions[index] = event.target.value
    updateFormField('questions', nextQuestions)
    setErrors((current) => ({ ...current, questions: undefined, form: undefined }))
  }

  function handleAddQuestion() {
    updateFormField('questions', [...form.questions, ''])
  }

  function handleRemoveQuestion(index: number) {
    updateFormField(
      'questions',
      form.questions.filter((_, questionIndex) => questionIndex !== index),
    )
    setErrors((current) => ({ ...current, questions: undefined, form: undefined }))
  }

  async function handleCreateRole(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSuccessMessage(null)

    const result = validateRoleForm(form)
    if ('errors' in result) {
      setErrors(result.errors)
      return
    }

    setIsSubmitting(true)
    setErrors({})

    try {
      const createdRole = await createRecruiterRole(result.payload)
      const nextCompanyId = createdRole.company_id

      setForm(createDefaultRoleForm(String(nextCompanyId)))
      setCompanyFilter(String(nextCompanyId))
      setIsCreatePanelOpen(false)
      setSuccessMessage(`Role "${createdRole.title}" was created successfully.`)
      await loadRolesForCompany(nextCompanyId)
    } catch (error) {
      setErrors({ form: getRoleErrorMessage(error) })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <section className="space-y-8">
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(320px,0.95fr)]">
        <div className="rounded-[2rem] border border-border bg-surfaceAlt p-8 shadow-panel">
          <p className="type-kicker">
            Recruiter roles
          </p>
          <h2 className="type-display-hero mt-5 max-w-3xl">
            Configure role criteria, hidden keywords, and interview questions.
          </h2>
          <p className="type-body mt-5 max-w-2xl">
            This workspace is tuned to the existing recruiter API: role cards load
            by <code>company_id</code>, creation posts to the live
            <code> /api/recruiter/roles</code> contract, and the question set stays
            aligned with the backend&apos;s <code>list[str]</code> shape.
          </p>

          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            <div className="rounded-3xl border border-border bg-surface p-5">
              <p className="type-meta">Active company</p>
              <p className="type-stat mt-3">
                {loadedCompanyId ? `#${loadedCompanyId}` : 'Not loaded'}
              </p>
            </div>
            <div className="rounded-3xl border border-border bg-surface p-5">
              <p className="type-meta">Visible roles</p>
              <p className="type-stat mt-3">
                {roles.length}
              </p>
            </div>
            <div className="rounded-3xl border border-border bg-surface p-5">
              <p className="type-meta">Question minimum</p>
              <p className="type-stat mt-3">6 required</p>
            </div>
          </div>
        </div>

        <div className="rounded-[2rem] border border-border bg-surface p-8 shadow-panel">
          <form onSubmit={handleCompanyFilterSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="role-company-filter"
                className="text-sm font-medium text-textPrimary"
              >
                Company ID
              </label>
              <input
                id="role-company-filter"
                type="number"
                min="1"
                step="1"
                value={companyFilter}
                onChange={(event) => {
                  setCompanyFilter(event.target.value)
                  setLoadError(null)
                  setSuccessMessage(null)
                }}
                className="mt-2 w-full rounded-2xl border border-border bg-background px-4 py-3 text-base text-textPrimary outline-none transition placeholder:text-textSecondary/75 focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20"
                placeholder="1"
              />
              <p className="mt-2 text-sm leading-6 text-textSecondary">
                Use the company ID tied to your recruiter account or seeded demo
                company.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="submit"
                disabled={isLoading}
                className="inline-flex items-center justify-center rounded-full border border-navButtonActive bg-navButtonActive px-5 py-3 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover disabled:cursor-not-allowed disabled:opacity-70"
              >
                {isLoading ? 'Loading roles...' : 'Load roles'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setIsCreatePanelOpen((current) => !current)
                  setErrors({})
                  setForm((current) => ({
                    ...current,
                    companyId: companyFilter.trim() || DEFAULT_COMPANY_ID,
                  }))
                  setSuccessMessage(null)
                }}
                className="inline-flex items-center justify-center rounded-full border border-border bg-surfaceAlt px-5 py-3 text-sm font-semibold text-textPrimary transition hover:border-accentSecondary hover:bg-accentSecondary/15"
              >
                {isCreatePanelOpen ? 'Close panel' : 'Create role'}
              </button>
            </div>

            {loadError ? (
              <div className="rounded-3xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">
                {loadError}
              </div>
            ) : null}

            {successMessage ? (
              <div className="rounded-3xl border border-success/30 bg-success/12 px-4 py-3 text-sm text-textPrimary">
                {successMessage}
              </div>
            ) : null}
          </form>
        </div>
      </div>

      {isCreatePanelOpen ? (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,0.72fr)_minmax(360px,0.92fr)]">
          <div className="rounded-[2rem] border border-border bg-surfaceAlt p-8 shadow-panel">
            <p className="text-sm font-medium uppercase tracking-[0.32em] text-textSecondary">
              Role creation guide
            </p>
            <h3 className="mt-4 text-3xl font-semibold tracking-tight text-textPrimary">
              Keep the recruiter-side role definition tight and high signal.
            </h3>
            <div className="mt-6 space-y-4 text-sm leading-7 text-textSecondary">
              <p>
                Hidden keywords drive matching on the backend, so use them for the
                private signals you care about most: frameworks, domain experience,
                depth markers, or team-specific attributes.
              </p>
              <p>
                Score bounds use the backend&apos;s normalized format from
                <code> 0.0</code> to <code>1.0</code>. For example, a range of
                <code> 0.65</code> to <code>1.0</code> roughly targets candidates at
                65% and above.
              </p>
              <p>
                The question builder stores plain-text prompts as an ordered string
                array. Add at least six strong prompts so the interview flow has
                enough recruiter-defined context before AI generation kicks in.
              </p>
            </div>
          </div>

          <form
            onSubmit={handleCreateRole}
            className="rounded-[2rem] border border-border bg-surface p-8 shadow-panel"
          >
            <div className="grid gap-6">
              <div className="grid gap-6 sm:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-textPrimary" htmlFor="role-company-id">
                    company_id
                  </label>
                  <input
                    id="role-company-id"
                    type="number"
                    min="1"
                    step="1"
                    value={form.companyId}
                    onChange={(event) => {
                      updateFormField('companyId', event.target.value)
                      setErrors((current) => ({
                        ...current,
                        companyId: undefined,
                        form: undefined,
                      }))
                    }}
                    disabled={isSubmitting}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-base text-textPrimary outline-none transition placeholder:text-textSecondary/75 focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20 disabled:cursor-not-allowed disabled:opacity-70"
                    placeholder="1"
                  />
                  {errors.companyId ? (
                    <p className="text-sm text-error">{errors.companyId}</p>
                  ) : null}
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-textPrimary" htmlFor="role-title">
                    Role title
                  </label>
                  <input
                    id="role-title"
                    type="text"
                    value={form.title}
                    onChange={(event) => {
                      updateFormField('title', event.target.value)
                      setErrors((current) => ({
                        ...current,
                        title: undefined,
                        form: undefined,
                      }))
                    }}
                    disabled={isSubmitting}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-base text-textPrimary outline-none transition placeholder:text-textSecondary/75 focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20 disabled:cursor-not-allowed disabled:opacity-70"
                    placeholder="Founding Product Engineer"
                  />
                  {errors.title ? (
                    <p className="text-sm text-error">{errors.title}</p>
                  ) : null}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-textPrimary" htmlFor="role-description">
                  Description
                </label>
                <textarea
                  id="role-description"
                  rows={5}
                  value={form.description}
                  onChange={(event) => {
                    updateFormField('description', event.target.value)
                    setErrors((current) => ({
                      ...current,
                      description: undefined,
                      form: undefined,
                    }))
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
                <label className="text-sm font-medium text-textPrimary" htmlFor="role-keywords">
                  Hidden keywords
                </label>
                <textarea
                  id="role-keywords"
                  rows={4}
                  value={form.hiddenKeywords}
                  onChange={(event) => {
                    updateFormField('hiddenKeywords', event.target.value)
                    setErrors((current) => ({ ...current, form: undefined }))
                  }}
                  disabled={isSubmitting}
                  className="w-full rounded-[1.5rem] border border-border bg-background px-4 py-3 text-base text-textPrimary outline-none transition placeholder:text-textSecondary/75 focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20 disabled:cursor-not-allowed disabled:opacity-70"
                  placeholder={'distributed systems\nNext.js\nfounder energy'}
                />
                <p className="text-sm leading-6 text-textSecondary">
                  Separate keywords with commas or new lines. These stay hidden from
                  candidates and are sent as a string array.
                </p>
              </div>

              <div className="grid gap-6 sm:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-textPrimary" htmlFor="role-min-score">
                    Min score
                  </label>
                  <input
                    id="role-min-score"
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={form.minScore}
                    onChange={(event) => {
                      updateFormField('minScore', event.target.value)
                      setErrors((current) => ({
                        ...current,
                        minScore: undefined,
                        maxScore: undefined,
                        form: undefined,
                      }))
                    }}
                    disabled={isSubmitting}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-base text-textPrimary outline-none transition placeholder:text-textSecondary/75 focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20 disabled:cursor-not-allowed disabled:opacity-70"
                    placeholder="0.4"
                  />
                  <p className="text-sm text-textSecondary">
                    Current input: {form.minScore || '0.0'} ({formatPercent(Number(form.minScore) || 0)})
                  </p>
                  {errors.minScore ? (
                    <p className="text-sm text-error">{errors.minScore}</p>
                  ) : null}
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-textPrimary" htmlFor="role-max-score">
                    Max score
                  </label>
                  <input
                    id="role-max-score"
                    type="number"
                    min="0"
                    max="1"
                    step="0.01"
                    value={form.maxScore}
                    onChange={(event) => {
                      updateFormField('maxScore', event.target.value)
                      setErrors((current) => ({
                        ...current,
                        minScore: undefined,
                        maxScore: undefined,
                        form: undefined,
                      }))
                    }}
                    disabled={isSubmitting}
                    className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-base text-textPrimary outline-none transition placeholder:text-textSecondary/75 focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20 disabled:cursor-not-allowed disabled:opacity-70"
                    placeholder="1.0"
                  />
                  <p className="text-sm text-textSecondary">
                    Current input: {form.maxScore || '1.0'} ({formatPercent(Number(form.maxScore) || 0)})
                  </p>
                  {errors.maxScore ? (
                    <p className="text-sm text-error">{errors.maxScore}</p>
                  ) : null}
                </div>
              </div>

              <div className="rounded-[1.75rem] border border-border bg-surfaceAlt/65 p-5">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm font-medium uppercase tracking-[0.24em] text-textSecondary">
                      Interview questions
                    </p>
                    <p className="mt-2 text-sm leading-6 text-textSecondary">
                      {normalizedQuestionCount} of {MIN_REQUIRED_QUESTIONS} required
                      questions ready to submit.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleAddQuestion}
                    disabled={isSubmitting}
                    className="inline-flex items-center justify-center rounded-full border border-border bg-surface px-4 py-2 text-sm font-semibold text-textPrimary transition hover:border-accentSecondary hover:bg-accentSecondary/15 disabled:cursor-not-allowed disabled:opacity-70"
                  >
                    Add question
                  </button>
                </div>

                <div className="mt-5 space-y-3">
                  {form.questions.map((question, index) => (
                    <div
                      key={`question-${index}`}
                      className="flex flex-col gap-3 rounded-[1.5rem] border border-border bg-surface p-4 sm:flex-row sm:items-start"
                    >
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-accentHighlight text-sm font-semibold text-textPrimary">
                        {index + 1}
                      </div>
                      <div className="flex-1">
                        <input
                          type="text"
                          value={question}
                          onChange={(event) => handleQuestionChange(index, event)}
                          disabled={isSubmitting}
                          className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-base text-textPrimary outline-none transition placeholder:text-textSecondary/75 focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20 disabled:cursor-not-allowed disabled:opacity-70"
                          placeholder="Ask a role-specific question in plain text."
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveQuestion(index)}
                        disabled={isSubmitting || form.questions.length === 1}
                        className="inline-flex items-center justify-center rounded-full border border-border px-4 py-2 text-sm font-medium text-textSecondary transition hover:border-error/35 hover:bg-error/8 hover:text-error disabled:cursor-not-allowed disabled:opacity-50"
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
                  className="inline-flex items-center justify-center rounded-full border border-navButtonActive bg-navButtonActive px-6 py-3 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover disabled:cursor-not-allowed disabled:opacity-70"
                >
                  {isSubmitting ? 'Creating role...' : 'Create role'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setForm(createDefaultRoleForm(form.companyId || DEFAULT_COMPANY_ID))
                    setErrors({})
                    setSuccessMessage(null)
                  }}
                  disabled={isSubmitting}
                  className="inline-flex items-center justify-center rounded-full border border-border bg-surfaceAlt px-6 py-3 text-sm font-semibold text-textPrimary transition hover:border-accentSecondary hover:bg-accentSecondary/15 disabled:cursor-not-allowed disabled:opacity-70"
                >
                  Reset form
                </button>
              </div>
            </div>
          </form>
        </div>
      ) : null}

      <div className="space-y-4">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.32em] text-textSecondary">
              Existing roles
            </p>
            <h3 className="mt-2 text-2xl font-semibold text-textPrimary">
              {loadedCompanyId ? `Company #${loadedCompanyId}` : 'Load a company to view roles'}
            </h3>
          </div>
          <p className="text-sm leading-6 text-textSecondary">
            Cards show the role description, hidden keyword set, and stored question
            list coming back from the current recruiter API.
          </p>
        </div>

        {isLoading ? (
          <div className="rounded-[2rem] border border-border bg-surface p-8 text-center shadow-panel">
            <p className="text-sm font-medium uppercase tracking-[0.32em] text-textSecondary">
              Loading roles
            </p>
            <h4 className="mt-3 text-2xl font-semibold text-textPrimary">
              Pulling the latest recruiter role cards...
            </h4>
          </div>
        ) : roles.length ? (
          <div className="grid gap-5 lg:grid-cols-2 2xl:grid-cols-3">
            {roles.map((role) => (
              <article
                key={role.id}
                className="rounded-[2rem] border border-border bg-surface p-6 shadow-panel"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.28em] text-textSecondary">
                      Role #{role.id}
                    </p>
                    <h4 className="mt-3 text-2xl font-semibold tracking-tight text-textPrimary">
                      {role.title}
                    </h4>
                  </div>
                  <span className="rounded-full border border-accentSecondary/45 bg-accentSecondary/15 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-textPrimary">
                    {formatCreatedAt(role.created_at)}
                  </span>
                </div>

                <p className="mt-4 text-sm leading-7 text-textSecondary">
                  {role.description}
                </p>

                <div className="mt-6 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-3xl border border-border bg-surfaceAlt p-4">
                    <p className="text-sm text-textSecondary">Company</p>
                    <p className="mt-2 text-lg font-semibold text-textPrimary">
                      #{role.company_id}
                    </p>
                  </div>
                  <div className="rounded-3xl border border-border bg-surfaceAlt p-4">
                    <p className="text-sm text-textSecondary">Score range</p>
                    <p className="mt-2 text-lg font-semibold text-textPrimary">
                      {formatPercent(role.min_score)} to {formatPercent(role.max_score)}
                    </p>
                  </div>
                </div>

                <div className="mt-6">
                  <p className="text-sm font-medium text-textPrimary">
                    Hidden keywords
                  </p>
                  {role.keywords.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {role.keywords.map((keyword) => (
                        <span
                          key={`${role.id}-${keyword}`}
                          className="rounded-full border border-border bg-surfaceAlt px-3 py-1.5 text-sm font-medium text-textPrimary"
                        >
                          {keyword}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-3 text-sm leading-6 text-textSecondary">
                      No hidden keywords saved yet.
                    </p>
                  )}
                </div>

                <div className="mt-6">
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-medium text-textPrimary">
                      Questions
                    </p>
                    <span className="rounded-full border border-accentLeaf/45 bg-accentLeaf/18 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-textPrimary">
                      {role.questions.length} saved
                    </span>
                  </div>
                  <div className="mt-3 space-y-2">
                    {role.questions.map((question, index) => (
                      <div
                        key={`${role.id}-question-${index}`}
                        className="rounded-2xl border border-border bg-background px-4 py-3 text-sm leading-6 text-textPrimary"
                      >
                        <span className="mr-2 text-textSecondary">{index + 1}.</span>
                        {question}
                      </div>
                    ))}
                  </div>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="rounded-[2rem] border border-border bg-surface p-8 shadow-panel">
            <p className="text-sm font-medium uppercase tracking-[0.32em] text-textSecondary">
              No roles yet
            </p>
            <h4 className="mt-3 text-2xl font-semibold text-textPrimary">
              This company does not have any active roles yet.
            </h4>
            <p className="mt-4 max-w-3xl text-base leading-7 text-textSecondary">
              Open the create-role panel to add the first role, hidden keyword set,
              and recruiter question list for company #{loadedCompanyId ?? companyFilter}.
            </p>
          </div>
        )}
      </div>
    </section>
  )
}
