import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from 'react'
import type { PointerEvent, ReactNode } from 'react'

export type SwipeDirection = 'left' | 'right' | 'up' | 'down'

export type TinderCardHandle = {
  swipe: (dir?: SwipeDirection) => Promise<void>
  restoreCard: () => Promise<void>
}

type TinderCardProps = {
  children: ReactNode
  className?: string
  preventSwipe?: SwipeDirection[]
  onSwipe?: (dir: SwipeDirection) => void
  onCardLeftScreen?: () => void
}

type Offset = {
  x: number
  y: number
}

const SWIPE_THRESHOLD = 140

export const TinderCard = forwardRef<TinderCardHandle, TinderCardProps>(
  function TinderCard(
    {
      children,
      className,
      preventSwipe = [],
      onSwipe,
      onCardLeftScreen,
    },
    ref,
  ) {
    const [offset, setOffset] = useState<Offset>({ x: 0, y: 0 })
    const [isDragging, setIsDragging] = useState(false)
    const [isGone, setIsGone] = useState(false)
    const dragStart = useRef<{
      x: number
      y: number
      originX: number
      originY: number
    } | null>(null)
    const resetTimer = useRef<number | null>(null)

    useEffect(() => {
      return () => {
        if (resetTimer.current) {
          window.clearTimeout(resetTimer.current)
        }
      }
    }, [])

    function isPrevented(direction: SwipeDirection) {
      return preventSwipe.includes(direction)
    }

    function settleCard(nextOffset: Offset) {
      setOffset(nextOffset)
      setIsDragging(false)
    }

    function completeSwipe(direction: SwipeDirection) {
      if (isPrevented(direction)) {
        settleCard({ x: 0, y: 0 })
        return
      }

      const travelX =
        direction === 'left'
          ? -Math.max(window.innerWidth, 960)
          : direction === 'right'
            ? Math.max(window.innerWidth, 960)
            : 0
      const travelY =
        direction === 'up'
          ? -Math.max(window.innerHeight, 720)
          : direction === 'down'
            ? Math.max(window.innerHeight, 720)
            : 0

      setOffset({ x: travelX, y: travelY })
      setIsDragging(false)
      setIsGone(true)
      onSwipe?.(direction)

      if (resetTimer.current) {
        window.clearTimeout(resetTimer.current)
      }

      resetTimer.current = window.setTimeout(() => {
        onCardLeftScreen?.()
      }, 220)
    }

    function restoreCard() {
      if (resetTimer.current) {
        window.clearTimeout(resetTimer.current)
        resetTimer.current = null
      }

      setIsGone(false)
      settleCard({ x: 0, y: 0 })
    }

    useImperativeHandle(ref, () => ({
      async swipe(dir = 'right') {
        completeSwipe(dir)
      },
      async restoreCard() {
        restoreCard()
      },
    }))

    function handlePointerDown(event: PointerEvent<HTMLDivElement>) {
      if (isGone) {
        return
      }

      dragStart.current = {
        x: event.clientX,
        y: event.clientY,
        originX: offset.x,
        originY: offset.y,
      }
      setIsDragging(true)
      event.currentTarget.setPointerCapture(event.pointerId)
    }

    function handlePointerMove(event: PointerEvent<HTMLDivElement>) {
      if (!dragStart.current || isGone) {
        return
      }

      const deltaX = event.clientX - dragStart.current.x
      const deltaY = event.clientY - dragStart.current.y

      setOffset({
        x: dragStart.current.originX + deltaX,
        y: dragStart.current.originY + deltaY,
      })
    }

    function handlePointerEnd(event: PointerEvent<HTMLDivElement>) {
      if (!dragStart.current) {
        return
      }

      event.currentTarget.releasePointerCapture(event.pointerId)

      const deltaX = offset.x
      const deltaY = offset.y
      dragStart.current = null

      if (Math.abs(deltaX) >= Math.abs(deltaY) && Math.abs(deltaX) > SWIPE_THRESHOLD) {
        completeSwipe(deltaX > 0 ? 'right' : 'left')
        return
      }

      if (Math.abs(deltaY) > SWIPE_THRESHOLD) {
        completeSwipe(deltaY > 0 ? 'down' : 'up')
        return
      }

      restoreCard()
    }

    return (
      <div
        className={className}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerEnd}
        onPointerCancel={handlePointerEnd}
        style={{
          touchAction: 'pan-y',
          transform: `translate3d(${offset.x}px, ${offset.y}px, 0) rotate(${offset.x / 18}deg)`,
          transition: isDragging ? 'none' : 'transform 220ms ease, opacity 220ms ease',
          opacity: isGone ? 0 : 1,
        }}
      >
        {children}
      </div>
    )
  },
)

export default TinderCard
