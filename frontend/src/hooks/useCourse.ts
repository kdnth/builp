import { useCallback, useEffect, useState } from 'react'
import { getCourseFromApi, type CourseDetail } from '../lib/api'

export function useCourse(courseId: string | undefined) {
  const [course, setCourse] = useState<CourseDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  const load = useCallback(() => {
    if (!courseId) {
      setLoading(false)
      setNotFound(true)
      return () => {}
    }

    let cancelled = false
    setLoading(true)
    setNotFound(false)

    getCourseFromApi(courseId)
      .then((result) => {
        if (cancelled) return
        setCourse(result)
        setLoading(false)
      })
      .catch(() => {
        if (cancelled) return
        setNotFound(true)
        setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [courseId])

  useEffect(() => load(), [load])

  return { course, setCourse, loading, notFound, refetch: load }
}
