import { Alert } from '@mantine/core'
import { LightbulbIcon } from '@phosphor-icons/react'
import LessonMarkdown from './LessonMarkdown'

interface ActivityExplanationProps {
  explanation?: string | null
  show: boolean
}

export default function ActivityExplanation({
  explanation,
  show,
}: ActivityExplanationProps) {
  if (!show || !explanation) return null

  return (
    <Alert
      color="gray"
      radius="md"
      icon={<LightbulbIcon weight="fill" />}
      title="Why"
    >
      <LessonMarkdown inline>{explanation}</LessonMarkdown>
    </Alert>
  )
}
