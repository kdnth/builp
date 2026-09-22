import type { CodePractice } from './codePractice'
import type { InteractivePractice } from './interactivePractice'
import type { LessonPage } from './lessonPage'
import type { WrittenLesson } from './writtenLesson'

export interface Lesson {
  id: string
  title: string
  pages?: LessonPage[]
  writtenLesson?: WrittenLesson
  codePractices?: CodePractice[]
  interactivePractices?: InteractivePractice[]
}
