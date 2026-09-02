import type { Course } from '../types/course'

export function findCourse(
  courses: Course[],
  courseId: string,
): Course | undefined {
  return courses.find((course) => course.id === courseId)
}
