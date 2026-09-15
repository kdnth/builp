import { Alert, Badge, Button, Group, Paper, Stack, Text } from '@mantine/core'
import { useRef, useState } from 'react'
import CodeEditor from '../code-editor/CodeEditor'
import type {
  FunctionTestResult,
  LineDiagnostic,
  LogEntry,
} from '../code-runner/types'
import { useCodeRunner } from '../code-runner/useCodeRunner'
import type { CodePractice } from '../../types/codePractice'
import type { ActivityStatus } from '../../types/activityStatus'
import {
  failedMessages,
  passedMessages,
  pickRandomMessage,
} from '../../helpers/activityMessages'
import {
  buildStarterCode,
  parseFunctionSignature,
} from '../../helpers/functionSignature'
import ActivityHeader from './ActivityHeader'
import ActivityAlert from './ActivityAlert'
import ConsolePanel from './ConsolePanel'

type FunctionPractice = Extract<CodePractice, { type: 'function' }>

interface FunctionPracticeViewProps {
  view: FunctionPractice
}

function formatCall(functionName: string, input: unknown[]) {
  return `${functionName}(${input.map((i) => JSON.stringify(i)).join(', ')})`
}

function formatResultLine(result: FunctionTestResult, functionName: string) {
  const call = formatCall(functionName, result.testCase.input)
  if (result.error) {
    return `${call} → Error: ${result.error}`
  }
  return `${call} → ${JSON.stringify(result.actualOutput)} (expected ${JSON.stringify(result.testCase.expectedOutput)})`
}

export default function FunctionPracticeView({
  view,
}: FunctionPracticeViewProps) {
  const starterCode = buildStarterCode(view.functionSignature, view.language)
  const { name: functionName } = parseFunctionSignature(view.functionSignature)

  const [code, setCode] = useState(starterCode)
  const [status, setStatus] = useState<ActivityStatus>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [results, setResults] = useState<FunctionTestResult[] | null>(null)
  const [diagnostics, setDiagnostics] = useState<LineDiagnostic[]>([])
  const [consoleOutput, setConsoleOutput] = useState<{
    logs: LogEntry[]
    truncated: boolean
  } | null>(null)
  const { run, running, runnerState, retry } = useCodeRunner(view.language)
  const isPython = view.language === 'python'
  const runnerStarting = isPython && runnerState.status === 'loading'
  const runnerFailed = runnerState.status === 'failed'
  // Redo during a run makes that run stale, so its result is ignored.
  const runToken = useRef(0)

  const passed = status === 'correct'

  async function handleRun() {
    const token = ++runToken.current
    const outcome = await run(code, functionName, view.testSuite)
    if (token !== runToken.current) return
    setResults(outcome.results)
    setDiagnostics(outcome.diagnostics)
    setConsoleOutput({ logs: outcome.logs, truncated: outcome.logsTruncated })
    setStatus(outcome.allPassed ? 'correct' : 'incorrect')
    setMessage(
      pickRandomMessage(outcome.allPassed ? passedMessages : failedMessages),
    )
  }

  function handleRedo() {
    runToken.current += 1
    setCode(starterCode)
    setStatus(null)
    setMessage(null)
    setResults(null)
    setDiagnostics([])
    setConsoleOutput(null)
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
            <>
              <Badge color="grape" variant="light">
                Function Practice
              </Badge>
              <Badge color="gray" variant="light">
                {isPython ? 'Python' : 'JavaScript'}
              </Badge>
            </>
          }
        />
        <Text c="dimmed" size="sm">
          {view.description}
        </Text>
        <CodeEditor
          value={code}
          onChange={setCode}
          language={view.language}
          readOnly={passed}
          diagnostics={diagnostics}
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
                {result.passed ? '✓' : '✗'}{' '}
                {formatResultLine(result, functionName)}
              </Text>
            ))}
          </Stack>
        )}
        {consoleOutput && (
          <ConsolePanel
            logs={consoleOutput.logs}
            truncated={consoleOutput.truncated}
            labelForTest={(index) =>
              `Test ${index + 1}: ${formatCall(functionName, view.testSuite[index].input)}`
            }
          />
        )}
        <ActivityAlert status={status} message={message} />
        {runnerFailed && (
          <Alert
            color="red"
            radius="md"
            title="The code runner is not available"
          >
            <Stack gap="xs" align="flex-start">
              <Text size="sm">{runnerState.error}</Text>
              <Button size="xs" variant="light" color="red" onClick={retry}>
                Retry
              </Button>
            </Stack>
          </Alert>
        )}
        <Group justify="flex-end">
          <Button
            disabled={passed || runnerStarting || runnerFailed}
            loading={running}
            onClick={handleRun}
            color={
              status === 'incorrect' ? 'red' : passed ? 'green' : undefined
            }
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
            {passed
              ? 'All Tests Passed!'
              : runnerStarting
                ? runnerState.restarting
                  ? 'Restarting Python...'
                  : 'Loading Python...'
                : 'Run Tests'}
          </Button>
        </Group>
      </Stack>
    </Paper>
  )
}
