import { useCallback, useEffect, useState, useSyncExternalStore } from 'react'
import type { CodeLanguage } from '../../types/codeLanguage'
import type { TestCase } from '../../types/testCase'
import { toTestResult } from './compareOutput'
import { runners } from './runners'
import type { FunctionTestResult, LineDiagnostic, LogEntry } from './types'
import type { WorkerRunResult } from './workerClient'

export interface CodeRunOutcome {
  results: FunctionTestResult[]
  allPassed: boolean
  logs: LogEntry[]
  logsTruncated: boolean
  diagnostics: LineDiagnostic[]
}

function collectDiagnostics(
  run: WorkerRunResult,
  results: FunctionTestResult[],
): LineDiagnostic[] {
  if (run.status !== 'completed') return []
  const errors = run.setupError
    ? [run.setupError]
    : results.map((result) => ({ line: result.line, message: result.error }))
  const byKey = new Map<string, LineDiagnostic>()
  for (const { line, message } of errors) {
    if (line && message) byKey.set(`${line}:${message}`, { line, message })
  }
  return [...byKey.values()]
}

function toOutcome(
  testSuite: TestCase[],
  run: WorkerRunResult,
  timeoutMs: number,
): CodeRunOutcome {
  const failAll = (error: string) =>
    testSuite.map((testCase) => ({ testCase, passed: false, error }))

  let results: FunctionTestResult[]
  switch (run.status) {
    case 'timedOut':
      results = failAll(
        `Timed out after ${timeoutMs / 1000} seconds. Check for an infinite loop.`,
      )
      break
    case 'crashed':
      results = failAll(run.message)
      break
    case 'completed':
      results = run.setupError
        ? failAll(run.setupError.message)
        : testSuite.map((testCase, index) =>
            toTestResult(testCase, run.results[index]),
          )
      break
  }

  return {
    results,
    allPassed: results.every((result) => result.passed),
    logs: run.logs,
    logsTruncated: run.logsTruncated,
    diagnostics: collectDiagnostics(run, results),
  }
}

export function useCodeRunner(language: CodeLanguage) {
  const runner = runners[language]
  const runnerState = useSyncExternalStore(runner.subscribe, runner.getState)
  const [running, setRunning] = useState(false)

  useEffect(() => {
    void runner.start().catch(() => {})
  }, [runner])

  const retry = useCallback(() => {
    void runner.start().catch(() => {})
  }, [runner])

  const run = useCallback(
    async (
      code: string,
      functionName: string,
      testSuite: TestCase[],
    ): Promise<CodeRunOutcome> => {
      setRunning(true)
      try {
        const result = await runner.run({ code, functionName, testSuite })
        return toOutcome(testSuite, result, runner.timeoutMs)
      } finally {
        setRunning(false)
      }
    },
    [runner],
  )

  return { run, running, runnerState, retry }
}
