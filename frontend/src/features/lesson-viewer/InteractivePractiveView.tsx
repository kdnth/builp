import { Badge, Group, Paper, Stack, Text, Title } from '@mantine/core'
import type { InteractivePractice } from '../../types/interactivePractice'

interface InteractivePracticeViewProps {
  view: InteractivePractice
}
export default function InteractivePracticeView({
  view,
}: InteractivePracticeViewProps) {
  return (
    <Paper withBorder radius="md" p="lg" shadow="sm">
      <Stack gap="sm">
        <Title order={3}>{view.title}</Title>
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
      </Stack>
    </Paper>
  )
}
