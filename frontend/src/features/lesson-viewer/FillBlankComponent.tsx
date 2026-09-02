import { Button, Group, Paper, Stack, Text, TextInput } from '@mantine/core'
import type { FillBlank } from '../../types/fillBlank'
import { useEffect, useState } from 'react'
import type { ActivityStatus } from '../../types/activityStatus'
import {
  failedMessages,
  passedMessages,
  pickRandomMessage,
} from '../../helpers/activityMessages'
import ActivityHeader from './ActivityHeader'
import ActivityAlert from './ActivityAlert'

interface FillBlankComponentProps {
  activity: FillBlank
  onComplete: (activityId: string, isComplete: boolean) => void
}
export default function FillBlankComponent({
  activity,
  onComplete,
}: FillBlankComponentProps) {
  const token = '{{blank}}'
  const textParts = activity.text.split(token)
  const blanks = [...activity.blanks].sort((a, b) => a.position - b.position)

  const [answers, setAnswers] = useState<string[]>(() =>
    Array(blanks.length).fill(''),
  )
  const [results, setResults] = useState<boolean[] | null>(null)
  const [status, setStatus] = useState<ActivityStatus>(null)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    onComplete(activity.id, status === 'correct')
  }, [status, activity.id, onComplete])

  const passed = status === 'correct'

  function handleChange(idx: number, value: string) {
    const next = [...answers]
    next[idx] = value
    setAnswers(next)
    setResults(null)
    setStatus(null)
    setMessage(null)
  }

  function handleSubmit() {
    const next = blanks.map((blank, idx) => {
      const answer = answers[idx].trim().toLowerCase()
      return blank.accepted.some(
        (accepted) => accepted.trim().toLowerCase() === answer,
      )
    })
    const isCorrect = next.every(Boolean)
    setResults(next)
    setStatus(isCorrect ? 'correct' : 'incorrect')
    setMessage(pickRandomMessage(isCorrect ? passedMessages : failedMessages))
  }

  function handleRedo() {
    setAnswers(Array(blanks.length).fill(''))
    setResults(null)
    setStatus(null)
    setMessage(null)
  }

  return (
    <Paper withBorder radius="md" p="lg">
      <Stack gap={'md'}>
        <ActivityHeader
          title="Fill in the Blank"
          status={status}
          onRedo={handleRedo}
        />
        <Text>
          {activity.description != null
            ? activity.description
            : 'Fill in the blank'}
        </Text>
        <Group gap={'xs'}>
          {textParts.map((p, idx) => (
            <Group key={idx} gap={'xs'}>
              <Text>{p}</Text>
              {idx < blanks.length && (
                <TextInput
                  w={120}
                  value={answers[idx]}
                  onChange={(e) => handleChange(idx, e.currentTarget.value)}
                  disabled={passed}
                  error={results !== null && !results[idx]}
                  styles={{
                    input:
                      results !== null && results[idx]
                        ? { borderColor: 'var(--mantine-color-green-filled)' }
                        : undefined,
                  }}
                />
              )}
            </Group>
          ))}
        </Group>
        <ActivityAlert status={status} message={message} />
        <Button
          disabled={passed || answers.some((a) => a.trim() === '')}
          onClick={handleSubmit}
          color={status === 'incorrect' ? 'red' : passed ? 'green' : undefined}
          styles={{
            root: passed
              ? {
                  cursor: 'default',
                  backgroundColor: 'var(--mantine-color-green-filled)',
                  color: 'var(--mantine-color-white)',
                  border: 'none',
                }
              : undefined,
          }}
        >
          {passed ? 'Correct!' : 'Submit'}
        </Button>
      </Stack>
    </Paper>
  )
}
