import type { Course } from '../types/course'
import type { Unit } from '../types/unit'

export function isLessonComplete(
  completedLessonIds: Set<string>,
  lessonId: string,
): boolean {
  return completedLessonIds.has(lessonId)
}

export function isUnitComplete(
  completedLessonIds: Set<string>,
  unit: Unit,
): boolean {
  return unit.lessons.every((lesson) => completedLessonIds.has(lesson.id))
}

export function isCourseComplete(
  completedLessonIds: Set<string>,
  course: Course,
): boolean {
  return course.units.every((unit) => isUnitComplete(completedLessonIds, unit))
}

export function isLessonUnlocked(
  completedLessonIds: Set<string>,
  unit: Unit,
  lessonIndex: number,
): boolean {
  if (lessonIndex === 0) return true
  const previousLesson = unit.lessons[lessonIndex - 1]
  return isLessonComplete(completedLessonIds, previousLesson.id)
}

export function isUnitUnlocked(
  completedLessonIds: Set<string>,
  course: Course,
  unitIndex: number,
): boolean {
  if (unitIndex === 0) return true
  const previousUnit = course.units[unitIndex - 1]
  return isUnitComplete(completedLessonIds, previousUnit)
}

export function countCompletedLessons(
  completedLessonIds: Set<string>,
  course: Course,
): number {
  return course.units.reduce(
    (count, unit) =>
      count +
      unit.lessons.filter((lesson) => completedLessonIds.has(lesson.id)).length,
    0,
  )
}

export function countTotalLessons(course: Course): number {
  return course.units.reduce((count, unit) => count + unit.lessons.length, 0)
}
