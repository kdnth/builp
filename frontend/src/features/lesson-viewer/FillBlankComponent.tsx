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
  const [attempts, setAttempts] = useState(0)

  const maxAttempts = 3
  const passed = status === 'correct'
  const revealed = status === 'revealed'
  const resolved = passed || revealed

  useEffect(() => {
    onComplete(activity.id, resolved)
  }, [resolved, activity.id, onComplete])

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
    if (!isCorrect) {
      setAttempts((prev) => prev + 1)
    }
  }

  function handleShowAnswer() {
    setAnswers(blanks.map((blank) => blank.accepted[0]))
    setResults(blanks.map(() => true))
    setStatus('revealed')
    setMessage("Here's the answer.")
  }

  function handleRedo() {
    setAnswers(Array(blanks.length).fill(''))
    setResults(null)
    setStatus(null)
    setMessage(null)
    setAttempts(0)
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
                  disabled={resolved}
                  error={results !== null && !results[idx]}
                  styles={{
                    input:
                      results !== null && results[idx]
                        ? {
                            borderColor: `var(--mantine-color-${passed ? 'green' : 'yellow'}-filled)`,
                          }
                        : undefined,
                  }}
                />
              )}
            </Group>
          ))}
        </Group>
        <ActivityAlert status={status} message={message} />
        <Group gap="xs">
          <Button
            disabled={resolved || answers.some((a) => a.trim() === '')}
            onClick={handleSubmit}
            color={status === 'incorrect' ? 'red' : passed ? 'green' : undefined}
            styles={{
              root: resolved
                ? {
                    cursor: 'default',
                    backgroundColor: `var(--mantine-color-${passed ? 'green' : 'yellow'}-filled)`,
                    color: 'var(--mantine-color-white)',
                    border: 'none',
                  }
                : undefined,
            }}
          >
            {passed ? 'Correct!' : revealed ? 'Answer Revealed' : 'Submit'}
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
