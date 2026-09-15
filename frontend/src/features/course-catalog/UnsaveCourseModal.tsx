import { Alert, Button, Group, Modal, Stack, Text } from '@mantine/core'
import { WarningIcon } from '@phosphor-icons/react'

export default function UnsaveCourseModal({
  opened,
  courseTitle,
  working,
  onCancel,
  onConfirm,
}: {
  opened: boolean
  courseTitle: string
  working: boolean
  onCancel: () => void
  onConfirm: () => void
}) {
  return (
    <Modal
      opened={opened}
      onClose={onCancel}
      title="Remove from My Courses?"
      centered
    >
      <Stack gap="md">
        <Text size="sm">
          Are you sure you want to remove "{courseTitle}" from My Courses?
        </Text>
        <Alert
          color="red"
          variant="light"
          radius="md"
          icon={<WarningIcon size={20} weight="fill" />}
        >
          All of your progress in this course will be lost. You cannot undo
          this.
        </Alert>
        <Group justify="end">
          <Button variant="default" disabled={working} onClick={onCancel}>
            Cancel
          </Button>
          <Button color="red" loading={working} onClick={onConfirm}>
            Remove and lose progress
          </Button>
        </Group>
      </Stack>
    </Modal>
  )
}
