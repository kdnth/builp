import type { CodePractice } from '../types/codePractice'
import type { InteractiveActivity } from '../types/interactiveActivity'
import type { InteractivePractice } from '../types/interactivePractice'
import type { LessonView } from '../types/lessonView'
import type { MultipleChoice } from '../types/multipleChoice'
import type { WrittenLesson } from '../types/writtenLesson'

export function isWrittenLesson(view: LessonView): view is WrittenLesson {
  return (view as WrittenLesson).markdown !== undefined
}

export function isCodePractice(view: LessonView): view is CodePractice {
  return (view as CodePractice).type !== undefined
}

export function isInteractivePractice(
  view: LessonView,
): view is InteractivePractice {
  return (view as InteractivePractice).activities !== undefined
}
