import { useCallback, useEffect, useRef, useState } from 'react'
import { listCourses, type CourseSummary } from '../lib/api'
import type { CourseType } from '../types/course'

export function useCourses(params?: {
  q?: string
  tag?: string
  courseType?: CourseType
  ownerUserId?: string
  forUserId?: string
  limit?: number
  offset?: number
}) {
  const q = params?.q
  const tag = params?.tag
  const courseType = params?.courseType
  const ownerUserId = params?.ownerUserId
  const forUserId = params?.forUserId
  const limit = params?.limit
  const offset = params?.offset

  const [courses, setCourses] = useState<CourseSummary[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const requestId = useRef(0)

  const refetch = useCallback(async () => {
    const thisRequest = ++requestId.current
    setLoading(true)
    setError(null)
    try {
      const result = await listCourses({
        q,
        tag,
        courseType,
        ownerUserId,
        forUserId,
        limit,
        offset,
      })
      if (requestId.current !== thisRequest) return
      setCourses(result.items)
      setTotal(result.total)
    } catch {
      if (requestId.current !== thisRequest) return
      setError('Could not load courses.')
    } finally {
      if (requestId.current === thisRequest) setLoading(false)
    }
  }, [q, tag, courseType, ownerUserId, forUserId, limit, offset])

  useEffect(() => {
    void refetch()
  }, [refetch])

  return { courses, total, loading, error, refetch }
}
