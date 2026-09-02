import { Badge, Group, Paper, Stack, Title } from '@mantine/core'
import { Sandpack } from '@codesandbox/sandpack-react'
import type { CodePractice } from '../../types/codePractice'

type ComponentPractice = Extract<CodePractice, { type: 'component' }>

interface ComponentPracticeViewProps {
  view: ComponentPractice
}

function detectTemplate(files: Record<string, string>): 'react-ts' | 'react' {
  const isTypeScript = Object.keys(files).some(
    (path) => path.endsWith('.ts') || path.endsWith('.tsx'),
  )
  return isTypeScript ? 'react-ts' : 'react'
}

export default function ComponentPracticeView({ view }: ComponentPracticeViewProps) {
  return (
    <Paper withBorder radius="md" p="lg" shadow="sm">
      <Stack gap="sm">
        <Group justify="space-between" wrap="nowrap">
          <Title order={3}>{view.title}</Title>
          <Badge color="grape" variant="light">
            Component Practice
          </Badge>
        </Group>
        <Sandpack
          template={detectTemplate(view.starterFiles)}
          theme="auto"
          files={view.starterFiles}
          customSetup={{ dependencies: view.dependencies }}
          options={{ showConsole: true, editorHeight: 420 }}
        />
      </Stack>
    </Paper>
  )
}
