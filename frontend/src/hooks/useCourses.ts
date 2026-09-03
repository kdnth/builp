import { useCallback, useEffect, useRef, useState } from 'react'
import { listCourses, type CourseSummary } from '../lib/api'

export function useCourses(params?: { q?: string; tag?: string }) {
  const q = params?.q
  const tag = params?.tag

  const [courses, setCourses] = useState<CourseSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Search fires a new request on every debounced keystroke. Without this,
  // an earlier (broader) request resolving after a later (more specific)
  // one silently overwrites the correct, filtered result with the stale,
  // unfiltered one.
  const requestId = useRef(0)

  const refetch = useCallback(async () => {
    const thisRequest = ++requestId.current
    setLoading(true)
    setError(null)
    try {
      const result = await listCourses({ q, tag })
      if (requestId.current !== thisRequest) return
      setCourses(result)
    } catch {
      if (requestId.current !== thisRequest) return
      setError('Could not load courses.')
    } finally {
      if (requestId.current === thisRequest) setLoading(false)
    }
  }, [q, tag])

  useEffect(() => {
    void refetch()
  }, [refetch])

  return { courses, loading, error, refetch }
}
