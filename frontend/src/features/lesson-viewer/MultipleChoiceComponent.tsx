import { Button, Chip, ChipGroup, Paper, Stack, Text } from '@mantine/core'
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

  useEffect(() => {
    onComplete(activity.id, status === 'correct')
  }, [status, activity.id, onComplete])

  const passed = status === 'correct'

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
  }

  function handleRedo() {
    setValue(null)
    setStatus(null)
    setMessage(null)
  }

  const chipColor = status === 'incorrect' ? 'red' : passed ? 'green' : undefined

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
                disabled={passed}
                styles={{
                  label: passed
                    ? {
                        cursor: 'default',
                        backgroundColor: isSelected
                          ? 'var(--mantine-color-green-filled)'
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
        <Button
          disabled={value === null || passed}
          onClick={handleSubmit}
          color={chipColor}
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
