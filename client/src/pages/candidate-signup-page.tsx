import type { ChangeEvent, DragEvent, FormEvent } from 'react'
import { useEffect, useId, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiFetch } from '../lib/api'
import { useAuth } from '../contexts/auth-context'

const MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024
const ACCEPTED_FILE_TYPES = new Set([
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
])
const ACCEPTED_EXTENSIONS = ['.pdf', '.docx']
const SIGNUP_ENDPOINT = '/api/candidates/register'

type SignupErrors = {
  name?: string
  email?: string
  password?: string
  file?: string
  form?: string
}

type CandidateSignupResponse = {
  id: number
  score: number
  summary: string
  top_skills: string[]
}

function isAcceptedFile(file: File) {
  const normalizedName = file.name.toLowerCase()

  return (
    ACCEPTED_FILE_TYPES.has(file.type) ||
    ACCEPTED_EXTENSIONS.some((extension) => normalizedName.endsWith(extension))
  )
}

function validateFile(file: File | null) {
  if (!file) {
    return 'Please upload your resume as a PDF or DOCX file.'
  }

  if (!isAcceptedFile(file)) {
    return 'Only PDF and DOCX files are supported.'
  }

  if (file.size > MAX_FILE_SIZE_BYTES) {
    return 'Resume files must be 5MB or smaller.'
  }

  return undefined
}

function validateEmail(email: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

function formatScore(score: number) {
  return Math.round(Math.max(0, Math.min(100, score)))
}

function getScoreTone(score: number) {
  if (score < 40) {
    return {
      stroke: '#D9776A',
      track: 'rgba(217, 119, 106, 0.18)',
      badge: 'bg-error/12 text-error border-error/30',
      label: 'Needs work',
    }
  }

  if (score < 70) {
    return {
      stroke: '#F0B56A',
      track: 'rgba(240, 181, 106, 0.2)',
      badge: 'bg-warning/15 text-textPrimary border-warning/35',
      label: 'Promising',
    }
  }

  return {
    stroke: '#7FA37A',
    track: 'rgba(127, 163, 122, 0.2)',
    badge: 'bg-success/15 text-textPrimary border-success/35',
    label: 'High match',
  }
}

function getSignupErrorMessage(error: unknown) {
  if (!(error instanceof Error)) {
    return 'We could not analyze your resume. Please try again.'
  }

  if (error.message.includes('status 409')) {
    return 'That email is already registered.'
  }

  if (
    error.message.includes('Resume text extraction produced unusable content')
  ) {
    return 'We could not read text from that PDF. Please upload a text-based PDF or DOCX rather than a scanned image.'
  }

  if (error.message.includes('Unsupported resume format')) {
    return 'Only PDF and DOCX files are supported right now.'
  }

  if (error.message.includes('status 422')) {
    return 'Your resume uploaded, but the parser could not extract enough readable text. Try exporting it again as a text-based PDF or use a DOCX file.'
  }

  if (error.message.includes('status 502')) {
    return 'Your resume was uploaded, but the analysis service is temporarily unavailable. Please try again in a moment.'
  }

  const detail = error.message.match(/status \d+(?::\s*)(.*)$/)?.[1]?.trim()
  return detail || 'We could not analyze your resume. Please try again.'
}

async function submitCandidateSignup(formData: FormData) {
  return apiFetch<CandidateSignupResponse>(SIGNUP_ENDPOINT, {
    method: 'POST',
    body: formData,
  })
}

export function CandidateSignupPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const inputId = useId()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [errors, setErrors] = useState<SignupErrors>({})
  const [isDragging, setIsDragging] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [result, setResult] = useState<CandidateSignupResponse | null>(null)
  const [autoLoginError, setAutoLoginError] = useState<string | null>(null)
  const [animatedScore, setAnimatedScore] = useState(0)

  const score = formatScore(result?.score ?? 0)
  const scoreTone = getScoreTone(score)
  const ringRadius = 70
  const ringCircumference = 2 * Math.PI * ringRadius
  const ringOffset =
    ringCircumference - (animatedScore / 100) * ringCircumference

  useEffect(() => {
    if (!result) {
      setAnimatedScore(0)
      return
    }

    const frame = window.requestAnimationFrame(() => {
      setAnimatedScore(score)
    })

    return () => window.cancelAnimationFrame(frame)
  }, [result, score])

  function updateFile(nextFile: File | null) {
    setResumeFile(nextFile)
    setErrors((current) => ({
      ...current,
      file: validateFile(nextFile),
      form: undefined,
    }))
  }

  function handleFileSelection(event: ChangeEvent<HTMLInputElement>) {
    updateFile(event.target.files?.[0] ?? null)
  }

  function handleDragOver(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault()
    setIsDragging(true)
  }

  function handleDragLeave(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault()
    setIsDragging(false)
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault()
    setIsDragging(false)
    updateFile(event.dataTransfer.files?.[0] ?? null)
  }

  function validateForm() {
    const nextErrors: SignupErrors = {}

    if (!name.trim()) {
      nextErrors.name = 'Please enter your full name.'
    }

    if (!email.trim()) {
      nextErrors.email = 'Please enter your email address.'
    } else if (!validateEmail(email)) {
      nextErrors.email = 'Please enter a valid email address.'
    }

    const fileError = validateFile(resumeFile)
    if (fileError) {
      nextErrors.file = fileError
    }

    setErrors(nextErrors)
    return Object.keys(nextErrors).length === 0
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (!validateForm() || !resumeFile) {
      return
    }

    setIsSubmitting(true)
    setErrors({})
    setAutoLoginError(null)

    const formData = new FormData()
    formData.append('name', name.trim())
    formData.append('email', email.trim())
    formData.append('resume', resumeFile)
    if (password) {
      formData.append('password', password)
    }

    try {
      const response = await submitCandidateSignup(formData)
      setResult(response)

      // Auto-login: backend always creates an AuthUser (password or default)
      try {
        const loginPassword = password || 'pomelo2026'
        await login(email.trim(), loginPassword)
      } catch {
        setAutoLoginError(
          'Your profile is ready, but we could not sign you in automatically. Continue to login to enter the feed.',
        )
      }
    } catch (error) {
      setErrors({
        form: getSignupErrorMessage(error),
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  if (result) {
    return (
      <section className="mx-auto grid max-w-5xl gap-8 lg:grid-cols-[1.05fr_0.95fr]">
        <div className="rounded-[2rem] border border-border bg-surfaceAlt p-8 shadow-panel">
          <p className="type-kicker">
            Resume analysis complete
          </p>
          <h2 className="type-display-page mt-5 max-w-2xl">
            You are ready to enter the curated role feed.
          </h2>
          <p className="type-body mt-5 max-w-2xl">
            Pomelo translated your resume into a candidate profile with a fit score,
            summary, and top skills to support higher-signal matching.
          </p>

          <div className="mt-8 grid gap-4 sm:grid-cols-3">
            <div className="rounded-3xl border border-border bg-surface p-5">
              <p className="type-meta">Candidate ID</p>
              <p className="type-stat mt-3">
                #{result.id}
              </p>
            </div>
            <div className="rounded-3xl border border-border bg-surface p-5">
              <p className="type-meta">Top skills</p>
              <p className="type-stat mt-3">
                {result.top_skills.length}
              </p>
            </div>
            <div className="rounded-3xl border border-border bg-surface p-5">
              <p className="type-meta">Assessment</p>
              <div
                className={`type-badge mt-3 inline-flex rounded-full border px-3 py-1 ${scoreTone.badge}`}
              >
                {scoreTone.label}
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-[2rem] border border-border bg-surface p-8 shadow-panel">
          <div className="flex flex-col items-center text-center">
            <div className="relative grid h-44 w-44 place-items-center">
              <svg
                viewBox="0 0 180 180"
                className="-rotate-90 h-full w-full"
                aria-hidden="true"
              >
                <circle
                  cx="90"
                  cy="90"
                  r={ringRadius}
                  fill="none"
                  stroke={scoreTone.track}
                  strokeWidth="14"
                />
                <circle
                  cx="90"
                  cy="90"
                  r={ringRadius}
                  fill="none"
                  stroke={scoreTone.stroke}
                  strokeWidth="14"
                  strokeLinecap="round"
                  strokeDasharray={ringCircumference}
                  strokeDashoffset={ringOffset}
                  style={{ transition: 'stroke-dashoffset 900ms ease-out' }}
                />
              </svg>
              <div className="absolute inset-6 rounded-full bg-surfaceAlt" />
              <div className="absolute text-center">
                <p className="font-ui text-xs uppercase tracking-[0.28em] text-textSecondary">
                  Score
                </p>
                <p className="type-counter mt-2 text-5xl">
                  {score}
                </p>
              </div>
            </div>

            <p className="type-kicker mt-8">
              AI summary
            </p>
            <p className="type-body mt-5">
              {result.summary}
            </p>

            <div className="mt-6 flex flex-wrap justify-center gap-2">
              {result.top_skills.map((skill) => (
                <span
                  key={skill}
                  className="font-ui rounded-full border border-border bg-surfaceAlt px-3 py-1.5 text-sm font-medium text-textPrimary"
                >
                  {skill}
                </span>
              ))}
            </div>

            {autoLoginError ? (
              <div className="mt-6 rounded-[1.25rem] border border-warning/35 bg-warning/16 px-4 py-3 text-sm text-textPrimary">
                {autoLoginError}
              </div>
            ) : null}

            <button
              type="button"
              onClick={() =>
                navigate(autoLoginError ? '/login' : '/candidate/feed')
              }
              className="font-ui mt-10 inline-flex items-center justify-center rounded-full border border-navButtonActive bg-navButtonActive px-6 py-3 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover"
            >
              {autoLoginError ? 'Continue to Login' : 'Start Swiping'}
            </button>
          </div>
        </div>
      </section>
    )
  }

  return (
    <section className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[0.95fr_1.05fr]">
      <div className="rounded-[2rem] border border-border bg-surfaceAlt p-8 shadow-panel">
        <p className="type-kicker">
          Candidate signup
        </p>
        <h2 className="type-display-hero mt-5 max-w-3xl">
          Upload your resume and let Pomelo build your matching profile.
        </h2>
        <p className="type-body-lg mt-5 max-w-2xl">
          Start the candidate flow by sharing your resume. We&apos;ll analyze your
          experience, create a structured summary, and prepare you for the curated
          role feed.
        </p>

        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <div className="rounded-3xl border border-border bg-surface p-5">
            <p className="type-meta">Accepted files</p>
            <p className="type-stat mt-3">
              PDF, DOCX
            </p>
          </div>
          <div className="rounded-3xl border border-border bg-surface p-5">
            <p className="type-meta">Max file size</p>
            <p className="type-stat mt-3">5MB</p>
          </div>
        </div>
      </div>

      <form
        onSubmit={handleSubmit}
        className="rounded-[2rem] border border-border bg-surface p-8 shadow-panel"
      >
        <div className="space-y-6">
          <div className="space-y-2">
            <label
              htmlFor={`${inputId}-name`}
              className="type-label"
            >
              Name
            </label>
            <input
              id={`${inputId}-name`}
              type="text"
              value={name}
              onChange={(event) => {
                setName(event.target.value)
                setErrors((current) => ({ ...current, name: undefined, form: undefined }))
              }}
              disabled={isSubmitting}
              className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-base text-textPrimary outline-none transition placeholder:text-textSecondary/75 focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20 disabled:cursor-not-allowed disabled:opacity-70"
              placeholder="Alex Morgan"
            />
            {errors.name ? (
              <p className="font-ui text-sm text-error">{errors.name}</p>
            ) : null}
          </div>

          <div className="space-y-2">
            <label
              htmlFor={`${inputId}-email`}
              className="type-label"
            >
              Email
            </label>
            <input
              id={`${inputId}-email`}
              type="email"
              value={email}
              onChange={(event) => {
                setEmail(event.target.value)
                setErrors((current) => ({ ...current, email: undefined, form: undefined }))
              }}
              disabled={isSubmitting}
              className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-base text-textPrimary outline-none transition placeholder:text-textSecondary/75 focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20 disabled:cursor-not-allowed disabled:opacity-70"
              placeholder="alex@pomelo.dev"
            />
            {errors.email ? (
              <p className="font-ui text-sm text-error">{errors.email}</p>
            ) : null}
          </div>

          <div className="space-y-2">
            <label
              htmlFor={`${inputId}-password`}
              className="type-label"
            >
              Password{' '}
              <span className="font-normal text-textSecondary">(optional)</span>
            </label>
            <input
              id={`${inputId}-password`}
              type="password"
              autoComplete="new-password"
              value={password}
              onChange={(event) => {
                setPassword(event.target.value)
                setErrors((current) => ({ ...current, password: undefined, form: undefined }))
              }}
              disabled={isSubmitting}
              className="w-full rounded-2xl border border-border bg-background px-4 py-3 text-base text-textPrimary outline-none transition placeholder:text-textSecondary/75 focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20 disabled:cursor-not-allowed disabled:opacity-70"
              placeholder="Set a password to sign in later"
            />
            <p className="font-ui text-xs text-textSecondary">
              Leave blank to use the demo default (pomelo2026)
            </p>
            {errors.password ? (
              <p className="font-ui text-sm text-error">{errors.password}</p>
            ) : null}
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <label className="type-label" htmlFor={inputId}>
                Resume upload
              </label>
              {resumeFile ? (
                <span className="type-meta">{resumeFile.name}</span>
              ) : null}
            </div>

            <label
              htmlFor={inputId}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={[
                'flex cursor-pointer flex-col items-center justify-center rounded-[1.75rem] border-2 border-dashed px-6 py-10 text-center transition',
                isDragging
                  ? 'border-accentPrimary bg-accentPrimary/10'
                  : 'border-border bg-surfaceAlt hover:border-accentSecondary hover:bg-accentSecondary/12',
                isSubmitting ? 'pointer-events-none opacity-70' : '',
              ].join(' ')}
            >
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-accentHighlight text-textPrimary">
                <svg
                  viewBox="0 0 24 24"
                  className="h-6 w-6"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  aria-hidden="true"
                >
                  <path d="M12 16V4" strokeLinecap="round" />
                  <path d="m7 9 5-5 5 5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M5 18.5h14" strokeLinecap="round" />
                </svg>
              </div>
              <p className="font-display mt-5 text-[1.7rem] font-semibold tracking-[-0.01em] text-textPrimary">
                Drag and drop your resume here
              </p>
              <p className="font-ui mt-3 max-w-sm text-sm leading-6 text-textSecondary">
                Upload a PDF or DOCX file up to 5MB, or click this area to browse
                from your device.
              </p>
              <span className="font-ui mt-6 inline-flex rounded-full border border-navButton bg-navButton px-4 py-2 text-sm font-medium text-navButtonText">
                Choose file
              </span>
            </label>

            <input
              ref={fileInputRef}
              id={inputId}
              type="file"
              accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              onChange={handleFileSelection}
              disabled={isSubmitting}
              className="sr-only"
            />

            {errors.file ? (
              <p className="font-ui text-sm text-error">{errors.file}</p>
            ) : (
              <p className="type-meta">
                Accepted formats: PDF or DOCX. Maximum size: 5MB.
              </p>
            )}
          </div>

          {errors.form ? (
            <div className="font-ui rounded-2xl border border-error/25 bg-error/10 px-4 py-3 text-sm text-textPrimary">
              {errors.form}
            </div>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="font-ui inline-flex w-full items-center justify-center rounded-full border border-navButtonActive bg-navButtonActive px-5 py-3 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover disabled:cursor-not-allowed disabled:opacity-70"
          >
            {isSubmitting ? 'Analyzing your resume...' : 'Create profile'}
          </button>
        </div>
      </form>
    </section>
  )
}
