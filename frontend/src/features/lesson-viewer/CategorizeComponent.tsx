import { Button, Group, Paper, Select, Stack, Text } from '@mantine/core'
import { useEffect, useMemo, useState } from 'react'
import {
  failedMessages,
  passedMessages,
  pickRandomMessage,
} from '../../helpers/activityMessages'
import { shuffle } from '../../helpers/shuffle'
import type { ActivityStatus } from '../../types/activityStatus'
import type { Categorize } from '../../types/categorize'
import ActivityAlert from './ActivityAlert'
import ActivityExplanation from './ActivityExplanation'
import ActivityHeader from './ActivityHeader'
import LessonMarkdown from './LessonMarkdown'

interface CategorizeComponentProps {
  activity: Categorize
  onComplete: (activityId: string, isComplete: boolean) => void
}

export default function CategorizeComponent({
  activity,
  onComplete,
}: CategorizeComponentProps) {
  const items = useMemo(() => shuffle(activity.items), [activity.items])
  const [answers, setAnswers] = useState<Record<string, string | null>>({})
  const [results, setResults] = useState<Record<string, boolean> | null>(null)
  const [status, setStatus] = useState<ActivityStatus>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [attempts, setAttempts] = useState(0)

  const maxAttempts = 3
  const passed = status === 'correct'
  const revealed = status === 'revealed'
  const resolved = passed || revealed
  const answered = items.every((item) => answers[item.id])

  useEffect(() => {
    onComplete(activity.id, resolved)
  }, [resolved, activity.id, onComplete])

  function handleChange(itemId: string, category: string | null) {
    setAnswers((previous) => ({ ...previous, [itemId]: category }))
    setResults(null)
    setStatus(null)
    setMessage(null)
  }

  function handleSubmit() {
    const next = Object.fromEntries(
      items.map((item) => [item.id, answers[item.id] === item.category]),
    )
    const isCorrect = Object.values(next).every(Boolean)
    setResults(next)
    setStatus(isCorrect ? 'correct' : 'incorrect')
    setMessage(pickRandomMessage(isCorrect ? passedMessages : failedMessages))
    if (!isCorrect) setAttempts((previous) => previous + 1)
  }

  function handleShowAnswer() {
    setAnswers(
      Object.fromEntries(
        activity.items.map((item) => [item.id, item.category]),
      ),
    )
    setResults(
      Object.fromEntries(activity.items.map((item) => [item.id, true])),
    )
    setStatus('revealed')
    setMessage('Here is where each one belongs.')
  }

  function handleRedo() {
    setAnswers({})
    setResults(null)
    setStatus(null)
    setMessage(null)
    setAttempts(0)
  }

  return (
    <Paper withBorder radius="md" p="lg">
      <Stack gap="md">
        <ActivityHeader
          title="Sort Into Groups"
          status={status}
          onRedo={handleRedo}
        />
        {activity.description && (
          <Text size="sm" c="dimmed">
            <LessonMarkdown inline>{activity.description}</LessonMarkdown>
          </Text>
        )}
        <Stack gap="xs">
          {items.map((item) => (
            <Group key={item.id} gap="sm" wrap="nowrap" align="center">
              <Text size="sm" style={{ flex: 1 }}>
                <LessonMarkdown inline>{item.text}</LessonMarkdown>
              </Text>
              <Select
                w={180}
                placeholder="Pick a group"
                value={answers[item.id] ?? null}
                onChange={(value) => handleChange(item.id, value)}
                data={activity.categories}
                disabled={resolved}
                error={results && !results[item.id] ? true : undefined}
                aria-label={`Group for ${item.text}`}
              />
            </Group>
          ))}
        </Stack>
        <ActivityAlert status={status} message={message} />
        <ActivityExplanation
          explanation={activity.explanation}
          show={resolved}
        />
        <Group gap="xs">
          <Button
            disabled={!answered || resolved}
            onClick={handleSubmit}
            color={passed ? 'green' : revealed ? 'yellow' : undefined}
          >
            {passed
              ? 'Correct!'
              : revealed
                ? 'Answer Revealed'
                : 'Check Groups'}
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
