import type { Course } from '../types/course'

const STORAGE_KEY = 'custom-courses'

export function loadCustomCourses(): Course[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed: unknown = JSON.parse(raw)
    return Array.isArray(parsed) ? (parsed as Course[]) : []
  } catch {
    return []
  }
}

export function saveCustomCourse(course: Course): Course[] {
  const next = [...loadCustomCourses(), course]
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // localStorage may be unavailable (private browsing, quota); the
    // course just won't persist across reloads in that case.
  }
  return next
}
