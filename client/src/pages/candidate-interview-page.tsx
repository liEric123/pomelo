import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../contexts/auth-context'
import { API_BASE_URL } from '../lib/api'

const THINKING_DURATION_SECONDS = 20
const RECORDING_DURATION_SECONDS = 120
const BREAK_DURATION_SECONDS = 15
const DEFAULT_TOTAL_QUESTIONS = 4
const FRAME_CAPTURE_INTERVAL_MS = 5000
const EMPTY_RESPONSE_FALLBACK =
  'Candidate completed a video response without a written summary.'

type InterviewPhase =
  | 'waiting'
  | 'thinking'
  | 'recording'
  | 'break'
  | 'completed'

type PromptKind = 'question' | 'follow_up'

type InterviewPrompt = {
  id: string
  text: string
  kind: PromptKind
  index: number
}

type InterviewQuestionMessage = {
  type: 'question'
  id: string | number
  index?: number
  text: string
  max_seconds?: number
}

type InterviewFollowUpMessage = {
  type: 'follow_up'
  text: string
}

type InterviewCompleteMessage = {
  type: 'interview_complete'
}

type InterviewErrorMessage = {
  type: 'error'
  detail: string
}

type InterviewInboundMessage =
  | InterviewQuestionMessage
  | InterviewFollowUpMessage
  | InterviewCompleteMessage
  | InterviewErrorMessage

function formatClock(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60

  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function getFooterMessage(phase: InterviewPhase, hasQueuedPrompt: boolean) {
  if (phase === 'break') {
    return 'Take a short break. Next question coming up...'
  }

  if (phase === 'completed') {
    return 'Interview complete. Your responses have been submitted for review.'
  }

  if (phase === 'recording') {
    return 'Stay steady and answer clearly. You can end the response early whenever you are finished.'
  }

  if (hasQueuedPrompt) {
    return 'Your next prompt is ready and will begin after this transition.'
  }

  return 'Prepare your response. The interview flow will guide each phase automatically.'
}

function toPrompt(
  message: InterviewQuestionMessage | InterviewFollowUpMessage,
  currentIndex = 0,
): InterviewPrompt {
  if (message.type === 'follow_up') {
    return {
      id: `follow-up-${crypto.randomUUID()}`,
      text: message.text,
      kind: 'follow_up',
      index: currentIndex,
    }
  }

  return {
    id: String(message.id),
    text: message.text,
    kind: 'question',
    index: message.index ?? 0,
  }
}

function buildInterviewSocketUrl(matchId: string, token: string | null | undefined) {
  const base = API_BASE_URL || window.location.origin
  const url = new URL(`/api/interviews/${matchId}/ws`, base)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  if (token) {
    url.searchParams.set('token', token)
  }
  return url.toString()
}

export function CandidateInterviewPage() {
  const { matchId = '' } = useParams()
  const navigate = useNavigate()
  const { session } = useAuth()
  const hasMatchId = Boolean(matchId)
  const [phase, setPhase] = useState<InterviewPhase>('waiting')
  const [secondsRemaining, setSecondsRemaining] = useState(THINKING_DURATION_SECONDS)
  const [currentPrompt, setCurrentPrompt] = useState<InterviewPrompt | null>(null)
  const [queuedPrompt, setQueuedPrompt] = useState<InterviewPrompt | null>(null)
  const [questionCount, setQuestionCount] = useState(1)
  const [questionTotal, setQuestionTotal] = useState(DEFAULT_TOTAL_QUESTIONS)
  const [websocketError, setWebsocketError] = useState<string | null>(null)
  const [cameraError, setCameraError] = useState<string | null>(null)
  const [cameraReady, setCameraReady] = useState(false)
  const [responseDraft, setResponseDraft] = useState('')
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const socketRef = useRef<WebSocket | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const responseStartedAtRef = useRef<number | null>(null)
  const responseDraftRef = useRef('')
  const reconnectCountRef = useRef(0)
  const manuallyClosedRef = useRef(false)
  const currentPromptRef = useRef<InterviewPrompt | null>(null)
  const phaseRef = useRef<InterviewPhase>('waiting')

  const questionCounterText = useMemo(
    () => `Q${questionCount}/${questionTotal}`,
    [questionCount, questionTotal],
  )
  const resolvedWebsocketError = hasMatchId
    ? websocketError
    : 'A match ID is required to open the interview.'

  const showVideoPreview = cameraReady

  function sendSocketMessage(payload: Record<string, unknown>) {
    const socket = socketRef.current
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return
    }

    socket.send(JSON.stringify(payload))
  }

  function activatePrompt(nextPrompt: InterviewPrompt) {
    setCurrentPrompt(nextPrompt)
    setResponseDraft('')
    setQuestionCount(nextPrompt.index + 1)
    setQuestionTotal((currentTotal) =>
      Math.max(currentTotal, nextPrompt.index + 1, DEFAULT_TOTAL_QUESTIONS),
    )
    setPhase('thinking')
    setSecondsRemaining(THINKING_DURATION_SECONDS)
  }

  function beginBreak() {
    responseStartedAtRef.current = null
    setPhase('break')
    setSecondsRemaining(BREAK_DURATION_SECONDS)
  }

  const finishRecording = useCallback(() => {
    if (phaseRef.current !== 'recording') {
      return
    }

    const elapsedSeconds = responseStartedAtRef.current
      ? Math.max(1, Math.round((Date.now() - responseStartedAtRef.current) / 1000))
      : 0
    const answerText = responseDraftRef.current.trim() || EMPTY_RESPONSE_FALLBACK

    sendSocketMessage({
      type: 'answer',
      text: answerText,
      elapsed_seconds: elapsedSeconds,
    })

    beginBreak()
  }, [])

  useEffect(() => {
    currentPromptRef.current = currentPrompt
  }, [currentPrompt])

  useEffect(() => {
    responseDraftRef.current = responseDraft
  }, [responseDraft])

  useEffect(() => {
    phaseRef.current = phase
  }, [phase])

  useEffect(() => {
    if (!hasMatchId) {
      return
    }

    manuallyClosedRef.current = false
    reconnectCountRef.current = 0
    let cancelled = false
    const token = session?.access_token ?? null

    function openSocket() {
      const socket = new WebSocket(buildInterviewSocketUrl(matchId, token))
      socketRef.current = socket

      socket.addEventListener('open', () => {
        if (cancelled) {
          return
        }

        setWebsocketError(null)
        reconnectCountRef.current = 0
      })

      socket.addEventListener('message', (event) => {
        try {
          const message = JSON.parse(event.data) as InterviewInboundMessage

          if (message.type === 'error') {
            setWebsocketError(message.detail)
            return
          }

          if (message.type === 'interview_complete') {
            setQueuedPrompt(null)
            setPhase('completed')
            setSecondsRemaining(0)
            return
          }

          const prompt = toPrompt(message, currentPromptRef.current?.index ?? 0)

          if (!currentPromptRef.current && phaseRef.current === 'waiting') {
            activatePrompt(prompt)
            return
          }

          setQueuedPrompt(prompt)
        } catch (error) {
          console.error('Failed to parse interview websocket message', error)
        }
      })

      socket.addEventListener('error', () => {
        if (!cancelled) {
          setWebsocketError('We lost the live interview connection. Trying again...')
        }
      })

      socket.addEventListener('close', () => {
        if (cancelled || manuallyClosedRef.current) {
          return
        }

        if (reconnectCountRef.current >= 2) {
          setWebsocketError('The interview connection could not be restored.')
          return
        }

        reconnectCountRef.current += 1
        window.setTimeout(() => {
          if (!cancelled) {
            openSocket()
          }
        }, reconnectCountRef.current * 1000)
      })
    }

    openSocket()

    return () => {
      cancelled = true
      manuallyClosedRef.current = true
      socketRef.current?.close()
      socketRef.current = null
    }
  }, [hasMatchId, matchId, session])

  useEffect(() => {
    let disposed = false

    async function requestCamera() {
      if (!navigator.mediaDevices?.getUserMedia) {
        setCameraError('This browser does not support webcam capture.')
        return
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: 'user',
          },
          audio: false,
        })

        if (disposed) {
          stream.getTracks().forEach((track) => track.stop())
          return
        }

        streamRef.current = stream
        setCameraReady(true)
        setCameraError(null)

        if (videoRef.current) {
          videoRef.current.srcObject = stream
        }
      } catch {
        setCameraReady(false)
        setCameraError('Camera access was denied. You can still continue, but live preview and frame capture will be unavailable.')
      }
    }

    void requestCamera()

    return () => {
      disposed = true
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      setCameraReady(false)
    }
  }, [])

  useEffect(() => {
    if (videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current
    }
  }, [cameraReady])

  useEffect(() => {
    if (phase === 'completed' || phase === 'waiting' || !currentPrompt) {
      return
    }

    const interval = window.setInterval(() => {
      setSecondsRemaining((current) => {
        if (current > 1) {
          return current - 1
        }

        if (phase === 'thinking') {
          responseStartedAtRef.current = Date.now()
          setPhase('recording')
          return RECORDING_DURATION_SECONDS
        }

        if (phase === 'recording') {
          finishRecording()
          return BREAK_DURATION_SECONDS
        }

        if (queuedPrompt) {
          activatePrompt(queuedPrompt)
          setQueuedPrompt(null)
          return THINKING_DURATION_SECONDS
        }

        setPhase('waiting')
        return 0
      })
    }, 1000)

    return () => {
      window.clearInterval(interval)
    }
  }, [currentPrompt, finishRecording, phase, queuedPrompt])

  useEffect(() => {
    if (phase !== 'recording' || !cameraReady || !videoRef.current || !canvasRef.current) {
      return
    }

    const interval = window.setInterval(() => {
      const video = videoRef.current
      const canvas = canvasRef.current

      if (
        !video ||
        !canvas ||
        !streamRef.current ||
        video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA
      ) {
        return
      }

      canvas.width = video.videoWidth || 640
      canvas.height = video.videoHeight || 360

      const context = canvas.getContext('2d')
      if (!context) {
        return
      }

      context.drawImage(video, 0, 0, canvas.width, canvas.height)
      const base64 = canvas.toDataURL('image/jpeg', 0.5)

      sendSocketMessage({
        type: 'frame',
        data: { base64 },
      })
    }, FRAME_CAPTURE_INTERVAL_MS)

    return () => {
      window.clearInterval(interval)
    }
  }, [cameraReady, phase])

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop())
      socketRef.current?.close()
    }
  }, [])

  const footerMessage = getFooterMessage(phase, Boolean(queuedPrompt))
  const canEditResponse =
    phase === 'thinking' || phase === 'recording' || phase === 'waiting'

  return (
    <section className="mx-auto flex h-[calc(100svh-2rem)] min-h-0 max-w-7xl">
      <canvas ref={canvasRef} className="hidden" />

      <div className="flex h-full min-h-0 w-full flex-col overflow-hidden rounded-[2rem] border border-white/70 bg-surface/90 shadow-[0_26px_72px_rgba(139,111,99,0.14)]">
        <div className="grid min-h-0 flex-1 overflow-hidden lg:grid-cols-[minmax(0,1.86fr)_minmax(300px,1fr)]">
          <div className="border-b border-border/80 px-6 py-5 sm:px-8 sm:py-6 lg:border-b-0 lg:border-r lg:border-border/80">
            <div className="flex h-full min-h-0 flex-col space-y-5">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-ui text-[1.45rem] font-semibold tracking-[-0.01em] text-[#b78968]">
                    {questionCounterText}
                  </p>
                  <div className="mt-2 h-px w-10 bg-border/90" />
                </div>
              </div>

              <div className="max-w-4xl pt-1">
                <h2 className="font-display text-[1.55rem] font-semibold leading-[1.22] tracking-[-0.01em] text-textPrimary sm:text-[2rem]">
                  {currentPrompt?.text ??
                    'Connecting to your interview session and preparing the first question.'}
                </h2>
              </div>

              <div className="border-t border-border/80 pt-5">
                <div className="mx-auto flex max-w-md flex-col items-center text-center">
                  <p className="font-ui text-[1.02rem] font-semibold text-textPrimary sm:text-[1.22rem]">
                    {phase === 'thinking'
                      ? 'Thinking Time: '
                      : phase === 'break'
                        ? 'Short Break: '
                        : phase === 'recording'
                          ? 'Response Time: '
                          : 'Interview Status: '}
                    <span
                      className={
                        phase === 'recording'
                          ? 'text-success'
                          : phase === 'break'
                            ? 'text-warning'
                            : 'text-accentPrimary'
                      }
                    >
                      {phase === 'completed' ? 'Done' : formatClock(secondsRemaining)}
                    </span>
                  </p>

                  <p className="font-ui mt-4 text-[0.98rem] italic leading-7 text-textSecondary sm:text-[1.02rem]">
                    {phase === 'thinking' && 'Prepare your response...'}
                    {phase === 'recording' && 'Recording in progress. Answer when you feel ready.'}
                    {phase === 'break' && 'Take a short breath before the next prompt.'}
                    {phase === 'waiting' &&
                      'We are lining up the next step in your interview flow.'}
                    {phase === 'completed' && 'You have completed the interview flow.'}
                  </p>
                </div>
              </div>

              <div className="mt-auto border-t border-border/80 pt-5">
                {resolvedWebsocketError ? (
                  <div className="font-ui rounded-[1.3rem] border border-error/20 bg-error/10 px-5 py-4 text-center text-sm leading-6 text-textPrimary">
                    {resolvedWebsocketError}
                  </div>
                ) : phase !== 'waiting' ? (
                  <div className="rounded-[1.45rem] border border-border/80 bg-surfaceAlt px-5 py-4">
                    <p className="font-ui text-[1rem] italic leading-7 text-textSecondary">
                      {phase === 'thinking' &&
                        'Get ready to start recording your answer in a moment...'}
                      {phase === 'recording' &&
                        'Your video response is live. Keep your answer focused and complete.'}
                      {phase === 'break' &&
                        'Pause, reset, and let the next question arrive naturally.'}
                      {phase === 'completed' &&
                        'Everything is submitted. You can leave the interview whenever you are ready.'}
                    </p>
                  </div>
                ) : null}
              </div>

              <div className="border-t border-border/80 pt-5">
                <div className="rounded-[1.45rem] border border-border/80 bg-surfaceAlt px-5 py-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-ui text-sm font-semibold text-textPrimary">
                        Written response summary
                      </p>
                      <p className="font-ui mt-1 text-sm leading-6 text-textSecondary">
                        Add a short transcript or bullet summary while you answer. This text is
                        sent with your response for grading and recruiter review.
                      </p>
                    </div>
                    <span className="font-ui shrink-0 rounded-full border border-border bg-surface px-3 py-1 text-xs text-textSecondary">
                      {responseDraft.trim().length} chars
                    </span>
                  </div>

                  <textarea
                    value={responseDraft}
                    onChange={(event) => setResponseDraft(event.target.value)}
                    disabled={!canEditResponse}
                    placeholder="Summarize your answer, outcomes, metrics, tradeoffs, and the examples you are discussing..."
                    className="font-ui mt-4 min-h-[180px] w-full rounded-[1.35rem] border border-border bg-surface px-4 py-3 text-sm leading-6 text-textPrimary outline-none transition placeholder:text-textSecondary/75 focus:border-accentPrimary focus:ring-2 focus:ring-accentPrimary/20 disabled:cursor-not-allowed disabled:opacity-70"
                  />

                  <p className="font-ui mt-3 text-xs leading-5 text-textSecondary">
                    If you leave this blank, Pomelo will send a generic fallback note and the
                    quality of grading will be lower.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <aside className="px-5 py-5 sm:px-6 sm:py-6">
            <div className="flex h-full min-h-0 flex-col space-y-4">
              <div className="rounded-[1.6rem] border border-border/75 bg-surfaceAlt/90 p-4 shadow-[0_16px_36px_rgba(139,111,99,0.1)]">
                <div className="space-y-2.5 text-center">
                  <p className="type-counter text-[2.65rem] sm:text-[3.25rem]">
                    {phase === 'recording'
                      ? formatClock(secondsRemaining)
                      : phase === 'completed'
                        ? '00:00'
                        : '02:00'}
                  </p>
                  <p className="font-ui text-base font-medium text-textPrimary">
                    {phase === 'recording'
                      ? 'Recording...'
                      : phase === 'thinking'
                        ? 'Waiting to record'
                        : phase === 'break'
                          ? 'Break in progress'
                          : phase === 'completed'
                            ? 'Interview complete'
                            : 'Preparing...'}
                  </p>
                </div>

                <div className="mt-4 overflow-hidden rounded-[1.35rem] border border-border/70 bg-[#ead9d0]">
                  {showVideoPreview ? (
                    <video
                      ref={videoRef}
                      autoPlay
                      playsInline
                      muted
                      className="aspect-[4/3] max-h-[210px] w-full object-cover [transform:scaleX(-1)]"
                    />
                  ) : (
                    <div className="flex aspect-[4/3] max-h-[210px] items-center justify-center px-6 text-center">
                      <div className="space-y-2.5">
                        <p className="font-display text-[1.7rem] font-semibold tracking-[-0.01em] text-textPrimary">
                          Camera preview waiting
                        </p>
                        <p className="type-body max-w-xs text-center">
                          {cameraError ??
                            'Once your camera stream is available, your mirrored preview will appear here.'}
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                <button
                  type="button"
                  onClick={finishRecording}
                  disabled={phase !== 'recording'}
                  className="font-ui mt-4 inline-flex w-full items-center justify-center rounded-[1rem] border border-navButtonActive bg-navButtonActive px-5 py-2.5 text-sm font-semibold text-navButtonText transition hover:border-navButtonHover hover:bg-navButtonHover disabled:cursor-not-allowed disabled:opacity-60"
                >
                  End Recording Early
                </button>
              </div>

              <div className="rounded-[1rem] border border-border bg-surface px-4 py-3 shadow-[0_12px_24px_rgba(139,111,99,0.08)]">
                <p className="font-ui text-sm leading-6 text-textSecondary">
                  Your camera preview and written summary stay in sync while you answer. Keep this
                  page open until the interview is fully complete.
                </p>
              </div>

              <button
                type="button"
                onClick={() => navigate('/candidate/matches')}
                className="font-ui inline-flex w-full items-center justify-center rounded-[1rem] border border-border bg-surfaceAlt px-5 py-2.5 text-sm font-semibold text-textPrimary transition hover:border-accentSecondary hover:bg-accentSecondary/12"
              >
                Leave interview
              </button>
            </div>
          </aside>
        </div>

        <div className="border-t border-border/80 px-6 py-3.5 text-center sm:px-8">
          <p className="font-ui text-[1rem] italic leading-7 text-textSecondary">
            {footerMessage}
          </p>
        </div>
      </div>
    </section>
  )
}
