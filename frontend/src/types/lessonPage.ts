import type { CodePractice } from './codePractice'
import type { InteractivePractice } from './interactivePractice'
import type { WrittenLesson } from './writtenLesson'

export type LessonPage =
  | { kind: 'written'; written: WrittenLesson }
  | { kind: 'code'; practice: CodePractice }
  | { kind: 'interactive'; practice: InteractivePractice }
