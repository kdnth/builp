import { Alert } from '@mantine/core'
import { CheckCircleIcon, XCircleIcon } from '@phosphor-icons/react'
import type { ActivityStatus } from '../../types/activityStatus'

interface ActivityAlertProps {
  status: ActivityStatus
  message: string | null
}

export default function ActivityAlert({ status, message }: ActivityAlertProps) {
  if (status === null || message === null) return null

  const isCorrect = status === 'correct'

  return (
    <Alert
      color={isCorrect ? 'green' : 'red'}
      icon={isCorrect ? <CheckCircleIcon weight="fill" /> : <XCircleIcon weight="fill" />}
      radius="md"
    >
      {message}
    </Alert>
  )
}
