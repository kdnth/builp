import { createContext, useContext, type ReactNode } from 'react'
import { useParams } from 'react-router-dom'
import { useCourseProgress } from './useCourseProgress'

type CourseProgressContextValue = ReturnType<typeof useCourseProgress>

const CourseProgressContext = createContext<CourseProgressContextValue | null>(
  null,
)

// Mounted once per course visit (see the /courses/:courseId parent route in
// App.tsx) so the tree page and unit pages share one progress state instead
// of each re-fetching from the server on navigation. A fresh fetch on every
// page mount could race an in-flight completeLesson call and momentarily
// report the lesson just finished as still incomplete.
export function CourseProgressProvider({ children }: { children: ReactNode }) {
  const { courseId } = useParams<{ courseId: string }>()
  const progress = useCourseProgress(courseId ?? '')

  return (
    <CourseProgressContext.Provider value={progress}>
      {children}
    </CourseProgressContext.Provider>
  )
}

export function useCourseProgressContext() {
  const value = useContext(CourseProgressContext)
  if (!value) {
    throw new Error(
      'useCourseProgressContext must be used within a CourseProgressProvider',
    )
  }
  return value
}
