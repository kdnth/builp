import { ActionIcon, Button, Group, Paper, Stack, Text } from '@mantine/core'
import { ArrowDownIcon, ArrowUpIcon } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import {
  failedMessages,
  passedMessages,
  pickRandomMessage,
} from '../../helpers/activityMessages'
import { shuffle } from '../../helpers/shuffle'
import type { ActivityStatus } from '../../types/activityStatus'
import type { Ordering } from '../../types/ordering'
import ActivityAlert from './ActivityAlert'
import ActivityExplanation from './ActivityExplanation'
import ActivityHeader from './ActivityHeader'
import LessonMarkdown from './LessonMarkdown'

interface OrderingComponentProps {
  activity: Ordering
  onComplete: (activityId: string, isComplete: boolean) => void
}

function shuffledOrder(items: string[]) {
  const indexes = items.map((_, index) => index)
  if (items.length < 2) return indexes
  let shuffled = shuffle(indexes)
  while (shuffled.every((value, index) => value === index)) {
    shuffled = shuffle(indexes)
  }
  return shuffled
}

export default function OrderingComponent({
  activity,
  onComplete,
}: OrderingComponentProps) {
  const [order, setOrder] = useState<number[]>(() =>
    shuffledOrder(activity.items),
  )
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

  function move(from: number, to: number) {
    if (resolved || to < 0 || to >= order.length) return
    const next = [...order]
    ;[next[from], next[to]] = [next[to], next[from]]
    setOrder(next)
    setStatus(null)
    setMessage(null)
  }

  function handleSubmit() {
    const isCorrect = order.every((value, index) => value === index)
    setStatus(isCorrect ? 'correct' : 'incorrect')
    setMessage(pickRandomMessage(isCorrect ? passedMessages : failedMessages))
    if (!isCorrect) setAttempts((previous) => previous + 1)
  }

  function handleShowAnswer() {
    setOrder(activity.items.map((_, index) => index))
    setStatus('revealed')
    setMessage('Here is the correct order.')
  }

  function handleRedo() {
    setOrder(shuffledOrder(activity.items))
    setStatus(null)
    setMessage(null)
    setAttempts(0)
  }

  return (
    <Paper withBorder radius="md" p="lg">
      <Stack gap="md">
        <ActivityHeader
          title="Put in Order"
          status={status}
          onRedo={handleRedo}
        />
        {activity.description && (
          <Text size="sm" c="dimmed">
            <LessonMarkdown inline>{activity.description}</LessonMarkdown>
          </Text>
        )}
        <Text size="sm" c="dimmed">
          Order: {activity.basis}
        </Text>
        <Stack gap="xs">
          {order.map((itemIndex, position) => (
            <Group
              key={itemIndex}
              gap="sm"
              wrap="nowrap"
              p="xs"
              style={{
                border: '1px solid var(--mantine-color-default-border)',
                borderRadius: 'var(--mantine-radius-md)',
              }}
            >
              <Text size="sm" c="dimmed" w={18} ta="center">
                {position + 1}
              </Text>
              <Text size="sm" style={{ flex: 1 }}>
                <LessonMarkdown inline>
                  {activity.items[itemIndex]}
                </LessonMarkdown>
              </Text>
              <ActionIcon.Group>
                <ActionIcon
                  variant="default"
                  disabled={resolved || position === 0}
                  aria-label="Move up"
                  onClick={() => move(position, position - 1)}
                >
                  <ArrowUpIcon size={14} />
                </ActionIcon>
                <ActionIcon
                  variant="default"
                  disabled={resolved || position === order.length - 1}
                  aria-label="Move down"
                  onClick={() => move(position, position + 1)}
                >
                  <ArrowDownIcon size={14} />
                </ActionIcon>
              </ActionIcon.Group>
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
            disabled={resolved}
            onClick={handleSubmit}
            color={passed ? 'green' : revealed ? 'yellow' : undefined}
          >
            {passed ? 'Correct!' : revealed ? 'Answer Revealed' : 'Check Order'}
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
