import course01 from './courses/course-01.json'
import type { Course } from '../types/course'

export const courses: Course[] = [course01 as Course]

export function getCourse(courseId: string): Course | undefined {
  return courses.find((course) => course.id === courseId)
}
