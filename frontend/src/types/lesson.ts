import type { CodePractice } from './codePractice'
import type { InteractivePractice } from './interactivePractice'
import type { WrittenLesson } from './writtenLesson'

export interface Lesson {
  id: string
  title: string
  writtenLesson: WrittenLesson
  codePractices: CodePractice[]
  interactivePractices: InteractivePractice[]
}
