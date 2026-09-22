import { Paper } from '@mantine/core'
import type { WrittenLesson } from '../../types/writtenLesson'
import LessonMarkdown from './LessonMarkdown'

interface WrittenLessonViewProps {
  view: WrittenLesson
}

export default function WrittenLessonView({ view }: WrittenLessonViewProps) {
  return (
    <Paper withBorder radius="md" p="lg" shadow="sm">
      <LessonMarkdown>{view.markdown}</LessonMarkdown>
    </Paper>
  )
}
