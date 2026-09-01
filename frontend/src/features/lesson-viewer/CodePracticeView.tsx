import type { CodePractice } from '../../types/codePractice'
import { Badge, Code, Group, Paper, Stack, Text, Title } from '@mantine/core'

interface CodePracticeViewProps {
  view: CodePractice
}

export default function CodePracticeView({ view }: CodePracticeViewProps) {
  const functionSignature =
    view.type === 'function'
      ? view.functionSignature
      : 'export default function Component()'

  const code = `// This is a temporary placeholder for CodePracticeViews\n${functionSignature} {\n\n}\n`

  return (
    <Paper withBorder radius="md" p="lg" shadow="sm">
      <Stack gap="sm">
        <Group justify="space-between" wrap="nowrap">
          <Title order={3}>{view.title}</Title>
          <Badge color="grape" variant="light">
            {view.type === 'function'
              ? 'Function Practice'
              : 'Component Practice'}
          </Badge>
        </Group>
        {view.type === 'function' && (
          <Text c="dimmed" size="sm">
            {view.description}
          </Text>
        )}
        <Code block>{code}</Code>
      </Stack>
    </Paper>
  )
}
