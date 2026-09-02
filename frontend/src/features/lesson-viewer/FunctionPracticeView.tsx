import { Badge, Button, Group, Paper, Stack, Text, Textarea } from '@mantine/core'
import { useState } from 'react'
import type { CodePractice } from '../../types/codePractice'
import type { ActivityStatus } from '../../types/activityStatus'
import {
  failedMessages,
  passedMessages,
  pickRandomMessage,
} from '../../helpers/activityMessages'
import { buildStarterCode, parseFunctionSignature } from '../../helpers/functionSignature'
import {
  runFunctionTests,
  type FunctionTestResult,
} from '../../helpers/runFunctionTests'
import ActivityHeader from './ActivityHeader'
import ActivityAlert from './ActivityAlert'

type FunctionPractice = Extract<CodePractice, { type: 'function' }>

interface FunctionPracticeViewProps {
  view: FunctionPractice
}

function formatResultLine(result: FunctionTestResult, functionName: string) {
  const call = `${functionName}(${result.testCase.input.map((i) => JSON.stringify(i)).join(', ')})`
  if (result.error) {
    return `${call} → Error: ${result.error}`
  }
  return `${call} → ${JSON.stringify(result.actualOutput)} (expected ${JSON.stringify(result.testCase.expectedOutput)})`
}

export default function FunctionPracticeView({ view }: FunctionPracticeViewProps) {
  const starterCode = buildStarterCode(view.functionSignature)
  const { name: functionName } = parseFunctionSignature(view.functionSignature)

  const [code, setCode] = useState(starterCode)
  const [status, setStatus] = useState<ActivityStatus>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [results, setResults] = useState<FunctionTestResult[] | null>(null)

  const passed = status === 'correct'

  function handleRun() {
    const { results: next, allPassed } = runFunctionTests(
      code,
      functionName,
      view.testSuite,
    )
    setResults(next)
    setStatus(allPassed ? 'correct' : 'incorrect')
    setMessage(pickRandomMessage(allPassed ? passedMessages : failedMessages))
  }

  function handleRedo() {
    setCode(starterCode)
    setStatus(null)
    setMessage(null)
    setResults(null)
  }

  return (
    <Paper withBorder radius="md" p="lg" shadow="sm">
      <Stack gap="sm">
        <ActivityHeader
          title={view.title}
          status={status}
          onRedo={handleRedo}
          titleOrder={3}
          extra={
            <Badge color="grape" variant="light">
              Function Practice
            </Badge>
          }
        />
        <Text c="dimmed" size="sm">
          {view.description}
        </Text>
        <Textarea
          value={code}
          onChange={(e) => setCode(e.currentTarget.value)}
          disabled={passed}
          autosize
          minRows={4}
          styles={{ input: { fontFamily: 'var(--mantine-font-family-monospace)' } }}
        />
        {results && (
          <Stack gap={4}>
            {results.map((result, idx) => (
              <Text
                key={idx}
                size="sm"
                c={result.passed ? 'green' : 'red'}
                ff="monospace"
              >
                {result.passed ? '✓' : '✗'} {formatResultLine(result, functionName)}
              </Text>
            ))}
          </Stack>
        )}
        <ActivityAlert status={status} message={message} />
        <Group justify="flex-end">
          <Button
            disabled={passed}
            onClick={handleRun}
            color={status === 'incorrect' ? 'red' : passed ? 'green' : undefined}
            styles={{
              root: passed
                ? {
                    cursor: 'default',
                    backgroundColor: 'var(--mantine-color-green-filled)',
                    color: 'var(--mantine-color-white)',
                    border: 'none',
                  }
                : undefined,
            }}
          >
            {passed ? 'All Tests Passed!' : 'Run Tests'}
          </Button>
        </Group>
      </Stack>
    </Paper>
  )
}
