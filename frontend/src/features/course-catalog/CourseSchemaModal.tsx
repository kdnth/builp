import { Code, Modal, ScrollArea, Stack, Text } from '@mantine/core'
import { courseJsonSchema } from '../../schemas/course'

interface CourseSchemaModalProps {
  opened: boolean
  onClose: () => void
}

export default function CourseSchemaModal({
  opened,
  onClose,
}: CourseSchemaModalProps) {
  return (
    <Modal opened={opened} onClose={onClose} title="Course JSON schema" size="lg">
      <Stack gap="sm">
        <Text size="sm" c="dimmed">
          Check your course file against this schema before you upload it.
        </Text>
        <ScrollArea.Autosize mah={500}>
          <Code block>{JSON.stringify(courseJsonSchema, null, 2)}</Code>
        </ScrollArea.Autosize>
      </Stack>
    </Modal>
  )
}
