import { useCallback, useEffect, useRef, useState } from 'react'
import { completeLesson, getProgress } from '../lib/api'
import { useAuthSession } from '../lib/auth'

export function useCourseProgress(courseId: string) {
  const session = useAuthSession()
  const isSignedIn = !session.isPending && session.data !== null

  const [completedLessonIds, setCompletedLessonIds] = useState<Set<string>>(
    () => new Set(),
  )

  // Lessons whose completion call has already been sent (or is in flight),
  // so a repeat call for the same lesson is a no-op instead of a second
  // network request. The backend already treats completing an
  // already-complete lesson as a no-op too, but a caller firing this
  // effect more than once for the same transition (a parent re-render
  // handing LessonComponent a fresh onComplete closure while its
  // active === pageCount condition is still true, for one real case seen
  // here) would otherwise send two requests to the same URL at once, and
  // one losing that race gets reported by the browser as a CORS failure
  // even though the real cause is just a redundant duplicate call.
  const syncedLessonIds = useRef<Set<string>>(new Set())

  useEffect(() => {
    if (!isSignedIn) {
      setCompletedLessonIds(new Set())
      syncedLessonIds.current = new Set()
      return
    }

    let cancelled = false
    getProgress(courseId)
      .then((result) => {
        if (cancelled) return
        const ids = new Set(result.completed_lesson_ids)
        setCompletedLessonIds(ids)
        syncedLessonIds.current = new Set(ids)
      })
      .catch(() => {
        if (!cancelled) setCompletedLessonIds(new Set())
      })

    return () => {
      cancelled = true
    }
  }, [courseId, isSignedIn])

  const markLessonComplete = useCallback(
    (lessonId: string) => {
      if (!isSignedIn) return

      // Optimistic: reflect it immediately, sync in the background. A
      // transient failure here just means this one lesson looks
      // uncompleted again next load, not a broken UI right now.
      setCompletedLessonIds((prev) => {
        if (prev.has(lessonId)) return prev
        const next = new Set(prev)
        next.add(lessonId)
        return next
      })

      if (syncedLessonIds.current.has(lessonId)) return
      syncedLessonIds.current.add(lessonId)
      void completeLesson(courseId, lessonId).catch(() => {
        // let a later call retry, since this one never actually landed
        syncedLessonIds.current.delete(lessonId)
      })
    },
    [courseId, isSignedIn],
  )

  return { completedLessonIds, markLessonComplete, isSignedIn }
}
