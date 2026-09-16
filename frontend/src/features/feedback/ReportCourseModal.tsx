import { useState } from 'react'
import {
  Alert,
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Text,
  Textarea,
} from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { CheckCircleIcon, WarningCircleIcon } from '@phosphor-icons/react'
import { reportCourseProblem, type ReportCategory } from '../../lib/api'

const CATEGORY_OPTIONS: { value: ReportCategory; label: string }[] = [
  { value: 'incorrect_content', label: 'Something is factually wrong' },
  { value: 'broken_code_practice', label: 'A code practice is broken' },
  { value: 'typo_or_formatting', label: 'Typo or formatting' },
  { value: 'inappropriate_content', label: 'Inappropriate content' },
  { value: 'other', label: 'Something else' },
]

interface ReportCourseModalProps {
  opened: boolean
  onClose: () => void
  courseId: string
  courseTitle: string
  lessonId?: string
}

export default function ReportCourseModal({
  opened,
  onClose,
  courseId,
  courseTitle,
  lessonId,
}: ReportCourseModalProps) {
  const [category, setCategory] = useState<ReportCategory>('incorrect_content')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function handleClose() {
    setError(null)
    onClose()
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await reportCourseProblem(courseId, {
        category,
        message: message.trim(),
        ...(lessonId ? { lesson_id: lessonId } : {}),
      })
      notifications.show({
        color: 'green',
        icon: <CheckCircleIcon weight="fill" size={20} />,
        title: 'Report sent',
        message: 'The author has been notified. Thanks for flagging it.',
      })
      setMessage('')
      setCategory('incorrect_content')
      onClose()
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Could not send your report.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      opened={opened}
      onClose={handleClose}
      title="Report a problem"
      centered
    >
      <form onSubmit={handleSubmit}>
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Reporting a problem in <strong>{courseTitle}</strong>
            {lessonId ? ', on the lesson you are viewing' : ''}. The author gets
            a notification, and it reaches support@kdnth.co.
          </Text>

          {error && (
            <Alert
              color="red"
              icon={<WarningCircleIcon weight="fill" size={20} />}
            >
              {error}
            </Alert>
          )}

          <Select
            label="What is wrong?"
            data={CATEGORY_OPTIONS}
            value={category}
            onChange={(value) =>
              setCategory((value as ReportCategory) ?? 'other')
            }
            allowDeselect={false}
            comboboxProps={{ withinPortal: true }}
          />
          <Textarea
            label="Details"
            description="What did you expect, and what happened instead?"
            value={message}
            onChange={(e) => setMessage(e.currentTarget.value)}
            minRows={5}
            maxLength={5000}
            autosize
            required
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={handleClose} type="button">
              Cancel
            </Button>
            <Button type="submit" loading={submitting}>
              Send report
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  )
}
