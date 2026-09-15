import { Box, ScrollArea, Stack, Text } from '@mantine/core'
import type { LogEntry } from '../code-runner/types'

interface ConsolePanelProps {
  logs: LogEntry[]
  truncated: boolean
  labelForTest: (testIndex: number) => string
}

interface LogGroup {
  testIndex: number | null
  entries: LogEntry[]
}

function groupLogs(logs: LogEntry[]): LogGroup[] {
  const groups: LogGroup[] = []
  for (const entry of logs) {
    const last = groups.at(-1)
    if (last && last.testIndex === entry.testIndex) {
      last.entries.push(entry)
    } else {
      groups.push({ testIndex: entry.testIndex, entries: [entry] })
    }
  }
  return groups
}

export default function ConsolePanel({
  logs,
  truncated,
  labelForTest,
}: ConsolePanelProps) {
  if (logs.length === 0 && !truncated) return null

  return (
    <Box
      style={{
        border: '1px solid var(--mantine-color-default-border)',
        borderRadius: 'var(--mantine-radius-md)',
        backgroundColor: 'var(--mantine-color-default-hover)',
      }}
    >
      <Text size="xs" fw={600} c="dimmed" tt="uppercase" px="sm" pt="xs">
        Console
      </Text>
      <ScrollArea.Autosize mah={260} type="auto">
        <Stack gap="xs" px="sm" pb="xs" pt={4}>
          {groupLogs(logs).map((group, groupIdx) => (
            <Box key={groupIdx}>
              <Text size="xs" c="dimmed" ff="monospace">
                {group.testIndex === null
                  ? 'Top-level code'
                  : labelForTest(group.testIndex)}
              </Text>
              {group.entries.map((entry, entryIdx) => (
                <Text
                  key={entryIdx}
                  component="pre"
                  size="sm"
                  ff="monospace"
                  c={entry.stream === 'stderr' ? 'red' : undefined}
                  m={0}
                  style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}
                >
                  {entry.text}
                </Text>
              ))}
            </Box>
          ))}
          {truncated && (
            <Text size="xs" c="dimmed" fs="italic">
              Output truncated
            </Text>
          )}
        </Stack>
      </ScrollArea.Autosize>
    </Box>
  )
}
