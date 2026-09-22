import type { Lesson } from '../types/lesson'
import type { LessonView } from '../types/lessonView'

export function lessonPages(lesson: Lesson): LessonView[] {
  if (lesson.pages?.length) {
    return lesson.pages.map((page) =>
      page.kind === 'written' ? page.written : page.practice,
    )
  }

  return [
    ...(lesson.writtenLesson ? [lesson.writtenLesson] : []),
    ...(lesson.codePractices ?? []),
    ...(lesson.interactivePractices ?? []),
  ]
}
