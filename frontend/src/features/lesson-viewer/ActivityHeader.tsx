import type { ReactNode } from 'react'
import { ActionIcon, Group, Title, Tooltip } from '@mantine/core'
import { ArrowCounterClockwiseIcon, CheckCircleIcon } from '@phosphor-icons/react'
import type { ActivityStatus } from '../../types/activityStatus'

interface ActivityHeaderProps {
  title: string
  status: ActivityStatus
  onRedo: () => void
  titleOrder?: 1 | 2 | 3 | 4 | 5 | 6
  extra?: ReactNode
}

export default function ActivityHeader({
  title,
  status,
  onRedo,
  titleOrder = 4,
  extra,
}: ActivityHeaderProps) {
  const color =
    status === 'correct'
      ? 'green'
      : status === 'incorrect'
        ? 'red'
        : status === 'revealed'
          ? 'yellow'
          : undefined

  return (
    <Group justify="between">
      <Title order={titleOrder}>{title}</Title>
      <Group gap="xs">
        {extra}
        <CheckCircleIcon color={color} weight={status === 'correct' ? 'fill' : 'regular'} />
        <Tooltip label="Start over">
          <ActionIcon
            variant="subtle"
            color="gray"
            onClick={onRedo}
            aria-label="Start over"
          >
            <ArrowCounterClockwiseIcon size={16} />
          </ActionIcon>
        </Tooltip>
      </Group>
    </Group>
  )
}
