import { Button, Group, NumberInput, Paper, Stack, Text } from '@mantine/core'
import { useEffect, useState } from 'react'
import {
  failedMessages,
  passedMessages,
  pickRandomMessage,
} from '../../helpers/activityMessages'
import type { ActivityStatus } from '../../types/activityStatus'
import type { Numeric } from '../../types/numeric'
import ActivityAlert from './ActivityAlert'
import ActivityExplanation from './ActivityExplanation'
import ActivityHeader from './ActivityHeader'
import LessonMarkdown from './LessonMarkdown'

interface NumericComponentProps {
  activity: Numeric
  onComplete: (activityId: string, isComplete: boolean) => void
}

export default function NumericComponent({
  activity,
  onComplete,
}: NumericComponentProps) {
  const [value, setValue] = useState<string | number>('')
  const [status, setStatus] = useState<ActivityStatus>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [attempts, setAttempts] = useState(0)

  const maxAttempts = 3
  const passed = status === 'correct'
  const revealed = status === 'revealed'
  const resolved = passed || revealed

  useEffect(() => {
    onComplete(activity.id, resolved)
  }, [resolved, activity.id, onComplete])

  function handleSubmit() {
    const answer = typeof value === 'number' ? value : Number(value)
    const isCorrect =
      Number.isFinite(answer) &&
      Math.abs(answer - activity.answer) <= Math.max(activity.tolerance, 1e-9)
    setStatus(isCorrect ? 'correct' : 'incorrect')
    setMessage(pickRandomMessage(isCorrect ? passedMessages : failedMessages))
    if (!isCorrect) setAttempts((previous) => previous + 1)
  }

  function handleShowAnswer() {
    setValue(activity.answer)
    setStatus('revealed')
    setMessage(
      `The answer is ${activity.answer}${activity.unit ? ` ${activity.unit}` : ''}.`,
    )
  }

  function handleRedo() {
    setValue('')
    setStatus(null)
    setMessage(null)
    setAttempts(0)
  }

  return (
    <Paper withBorder radius="md" p="lg">
      <Stack gap="md">
        <ActivityHeader
          title="Work It Out"
          status={status}
          onRedo={handleRedo}
        />
        {activity.description && (
          <Text size="sm" c="dimmed">
            <LessonMarkdown inline>{activity.description}</LessonMarkdown>
          </Text>
        )}
        <Text>
          <LessonMarkdown inline>{activity.question}</LessonMarkdown>
        </Text>
        <NumberInput
          value={value}
          onChange={(next) => {
            setValue(next)
            setStatus(null)
            setMessage(null)
          }}
          disabled={resolved}
          placeholder="Your answer"
          suffix={activity.unit ? ` ${activity.unit}` : undefined}
          w={220}
          aria-label="Your answer"
        />
        <ActivityAlert status={status} message={message} />
        <ActivityExplanation
          explanation={activity.explanation}
          show={resolved}
        />
        <Group gap="xs">
          <Button
            disabled={value === '' || resolved}
            onClick={handleSubmit}
            color={passed ? 'green' : revealed ? 'yellow' : undefined}
          >
            {passed
              ? 'Correct!'
              : revealed
                ? 'Answer Revealed'
                : 'Check Answer'}
          </Button>
          {!resolved && attempts >= maxAttempts && (
            <Button variant="outline" color="yellow" onClick={handleShowAnswer}>
              Show Answer
            </Button>
          )}
        </Group>
      </Stack>
    </Paper>
  )
}
