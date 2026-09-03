import { Alert, Badge, Group, Paper, Stack, Text, Title } from '@mantine/core'
import { CheckCircleIcon } from '@phosphor-icons/react'
import { useCallback, useEffect, useState } from 'react'
import type { InteractivePractice } from '../../types/interactivePractice'
import ActivityComponentRenderer from './ActivityComponentRenderer'

interface InteractivePracticeViewProps {
  view: InteractivePractice
  onAllActivitiesComplete?: (practiceId: string, allComplete: boolean) => void
}
export default function InteractivePracticeView({
  view,
  onAllActivitiesComplete,
}: InteractivePracticeViewProps) {
  const [completed, setCompleted] = useState<Record<string, boolean>>({})

  const handleActivityComplete = useCallback(
    (activityId: string, isComplete: boolean) => {
      setCompleted((prev) =>
        prev[activityId] === isComplete
          ? prev
          : { ...prev, [activityId]: isComplete },
      )
    },
    [],
  )

  const total = view.activities.length
  const completedCount = Object.values(completed).filter(Boolean).length
  const allComplete = total > 0 && completedCount === total
  const readyToProceed = total === 0 || completedCount === total

  useEffect(() => {
    onAllActivitiesComplete?.(view.id, readyToProceed)
  }, [readyToProceed, view.id, onAllActivitiesComplete])

  return (
    <Paper withBorder radius="md" p="lg" shadow="sm">
      <Stack gap="sm">
        <Group justify="between">
          <Title order={3}>{view.title}</Title>
          <Badge color={allComplete ? 'green' : 'gray'} variant="light">
            {completedCount}/{total}
          </Badge>
        </Group>
        <Text c="dimmed" size="sm">
          This is an interactive practice placeholder.
        </Text>
        <Group gap="xs">
          {view.activities.map((activity) => (
            <Badge key={activity.id} color="teal" variant="light">
              {activity.type}
            </Badge>
          ))}
        </Group>
        {allComplete && (
          <Alert color="green" icon={<CheckCircleIcon weight="fill" />} radius="md">
            Nice work! You've completed all the activities in this practice.
          </Alert>
        )}
        <Stack gap={'md'} align="stretch" justify="center">
          {view.activities.map((activity) => (
            <ActivityComponentRenderer
              key={activity.id}
              activity={activity}
              onComplete={handleActivityComplete}
            />
          ))}
        </Stack>
      </Stack>
    </Paper>
  )
}
