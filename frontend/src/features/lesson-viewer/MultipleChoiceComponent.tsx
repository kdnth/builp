import { Button, Chip, ChipGroup, Group, Paper, Stack, Text } from '@mantine/core'
import type { MultipleChoice } from '../../types/multipleChoice'
import { useEffect, useState } from 'react'
import type { ActivityStatus } from '../../types/activityStatus'
import {
  failedMessages,
  passedMessages,
  pickRandomMessage,
} from '../../helpers/activityMessages'
import ActivityHeader from './ActivityHeader'
import ActivityAlert from './ActivityAlert'

interface MultipleChoiceComponentProps {
  activity: MultipleChoice
  onComplete: (activityId: string, isComplete: boolean) => void
}
export default function MultipleChoiceComponent({
  activity,
  onComplete,
}: MultipleChoiceComponentProps) {
  const [value, setValue] = useState<string | null>(null)
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

  const handleChipClick = (event: React.MouseEvent<HTMLInputElement>) => {
    setStatus(null)
    setMessage(null)
    setValue(event.currentTarget.value === value ? null : event.currentTarget.value)
  }

  // as of right now nothing stops people from writing MCQ with >=8 questions
  const questionLabels = ['A', 'B', 'C', 'D', 'E', 'F', 'G']

  function handleSubmit() {
    const isCorrect = value !== null && Number.parseInt(value) === activity.correctIndex
    setStatus(isCorrect ? 'correct' : 'incorrect')
    setMessage(pickRandomMessage(isCorrect ? passedMessages : failedMessages))
    if (!isCorrect) {
      setAttempts((prev) => prev + 1)
    }
  }

  function handleShowAnswer() {
    setValue(activity.correctIndex.toString())
    setStatus('revealed')
    setMessage(`Here's the answer: ${questionLabels[activity.correctIndex]}. ${activity.options[activity.correctIndex]}`)
  }

  function handleRedo() {
    setValue(null)
    setStatus(null)
    setMessage(null)
    setAttempts(0)
  }

  const chipColor =
    status === 'incorrect' ? 'red' : passed ? 'green' : revealed ? 'yellow' : undefined

  return (
    <Paper withBorder radius="md" p="lg">
      <Stack gap={'md'} justify="center">
        <ActivityHeader
          title="Multiple Choice"
          status={status}
          onRedo={handleRedo}
        />
        <Text>{activity.question}</Text>
        <ChipGroup value={value} onChange={setValue}>
          {activity.options.map((o, idx) => {
            const isSelected = value === idx.toString()
            return (
              <Chip
                key={idx}
                value={idx.toString()}
                onClick={handleChipClick}
                icon={null}
                color={chipColor}
                disabled={resolved}
                styles={{
                  label: resolved
                    ? {
                        cursor: 'default',
                        backgroundColor: isSelected
                          ? `var(--mantine-color-${passed ? 'green' : 'yellow'}-filled)`
                          : 'transparent',
                        color: isSelected
                          ? 'var(--mantine-color-white)'
                          : 'var(--mantine-color-text)',
                      }
                    : undefined,
                }}
              >
                {questionLabels[idx]}. {o}
              </Chip>
            )
          })}
        </ChipGroup>
        <ActivityAlert status={status} message={message} />
        <Group gap="xs">
          <Button
            disabled={value === null || resolved}
            onClick={handleSubmit}
            color={chipColor}
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
