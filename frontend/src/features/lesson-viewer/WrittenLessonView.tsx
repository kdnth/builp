import Markdown from 'react-markdown'
import type { WrittenLesson } from '../../types/writtenLesson'
import { Paper, Typography } from '@mantine/core'

interface WrittenLessonViewProps {
  view: WrittenLesson
}

export default function WrittenLessonView({ view }: WrittenLessonViewProps) {
  return (
    <Paper withBorder radius="md" p="lg" shadow="sm">
      <Typography>
        <Markdown>{view.markdown}</Markdown>
      </Typography>
    </Paper>
  )
}
