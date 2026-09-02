import { useCallback, useState } from 'react'

function storageKey(courseId: string) {
  return `course-progress:${courseId}`
}

function loadCompletedLessonIds(courseId: string): Set<string> {
  try {
    const raw = localStorage.getItem(storageKey(courseId))
    if (!raw) return new Set()
    const parsed: unknown = JSON.parse(raw)
    return Array.isArray(parsed) ? new Set(parsed) : new Set()
  } catch {
    return new Set()
  }
}

function saveCompletedLessonIds(courseId: string, ids: Set<string>) {
  try {
    localStorage.setItem(storageKey(courseId), JSON.stringify([...ids]))
  } catch {
    // localStorage may be unavailable (private browsing, quota); progress
    // just won't persist across reloads in that case.
  }
}

export function useCourseProgress(courseId: string) {
  const [completedLessonIds, setCompletedLessonIds] = useState<Set<string>>(
    () => loadCompletedLessonIds(courseId),
  )

  const markLessonComplete = useCallback(
    (lessonId: string) => {
      setCompletedLessonIds((prev) => {
        if (prev.has(lessonId)) return prev
        const next = new Set(prev)
        next.add(lessonId)
        saveCompletedLessonIds(courseId, next)
        return next
      })
    },
    [courseId],
  )

  return { completedLessonIds, markLessonComplete }
}
