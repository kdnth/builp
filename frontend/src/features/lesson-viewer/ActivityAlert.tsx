import { Alert } from '@mantine/core'
import { CheckCircleIcon, InfoIcon, XCircleIcon } from '@phosphor-icons/react'
import type { ActivityStatus } from '../../types/activityStatus'

interface ActivityAlertProps {
  status: ActivityStatus
  message: string | null
}

export default function ActivityAlert({ status, message }: ActivityAlertProps) {
  if (status === null || message === null) return null

  const color =
    status === 'correct' ? 'green' : status === 'revealed' ? 'yellow' : 'red'
  const icon =
    status === 'correct' ? (
      <CheckCircleIcon weight="fill" />
    ) : status === 'revealed' ? (
      <InfoIcon weight="fill" />
    ) : (
      <XCircleIcon weight="fill" />
    )

  return (
    <Alert color={color} icon={icon} radius="md">
      {message}
    </Alert>
  )
}
