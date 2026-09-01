import {
  isCodePractice,
  isInteractivePractice,
  isWrittenLesson,
} from '../../helpers/typeGuards'
import type { LessonView } from '../../types/lessonView'
import CodePracticeView from './CodePracticeView'
import InteractivePracticeView from './InteractivePractiveView'
import WrittenLessonView from './WrittenLessonView'

interface LessonViewRendererProps {
  view: LessonView
}

export default function LessonViewRenderer({ view }: LessonViewRendererProps) {
  if (isWrittenLesson(view)) {
    return <WrittenLessonView view={view} />
  } else if (isCodePractice(view)) {
    return <CodePracticeView view={view} />
  } else if (isInteractivePractice(view)) {
    return <InteractivePracticeView view={view} />
  }
}
