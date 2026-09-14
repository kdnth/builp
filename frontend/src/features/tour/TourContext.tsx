import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import TourOverlay from './TourOverlay'

export interface TourStep {
  /** CSS selector for the element this step points at. */
  target: string
  title: string
  content: ReactNode
}

interface TourState {
  tourId: string
  steps: TourStep[]
  stepIndex: number
}

interface TourContextValue {
  tour: TourState | null
  start: (tourId: string, steps: TourStep[]) => void
  next: () => void
  back: () => void
  end: () => void
}

const TourContext = createContext<TourContextValue | null>(null)

function completedKey(tourId: string) {
  return `tour-completed:${tourId}`
}

export function hasCompletedTour(tourId: string) {
  try {
    return localStorage.getItem(completedKey(tourId)) === '1'
  } catch {
    return false
  }
}

function markCompleted(tourId: string) {
  try {
    localStorage.setItem(completedKey(tourId), '1')
  } catch {}
}

export function TourProvider({ children }: { children: ReactNode }) {
  const [tour, setTour] = useState<TourState | null>(null)

  const start = useCallback((tourId: string, steps: TourStep[]) => {
    if (steps.length === 0) return
    setTour({ tourId, steps, stepIndex: 0 })
  }, [])

  const end = useCallback(() => {
    setTour((current) => {
      if (current) markCompleted(current.tourId)
      return null
    })
  }, [])

  const next = useCallback(() => {
    setTour((current) => {
      if (!current) return current
      const nextIndex = current.stepIndex + 1
      if (nextIndex >= current.steps.length) {
        markCompleted(current.tourId)
        return null
      }
      return { ...current, stepIndex: nextIndex }
    })
  }, [])

  const back = useCallback(() => {
    setTour((current) =>
      current && current.stepIndex > 0
        ? { ...current, stepIndex: current.stepIndex - 1 }
        : current,
    )
  }, [])

  const value = useMemo(
    () => ({ tour, start, next, back, end }),
    [tour, start, next, back, end],
  )

  return (
    <TourContext.Provider value={value}>
      {children}
      <TourOverlay />
    </TourContext.Provider>
  )
}

export function useTour() {
  const ctx = useContext(TourContext)
  if (!ctx) throw new Error('useTour must be used within a TourProvider')
  return ctx
}
