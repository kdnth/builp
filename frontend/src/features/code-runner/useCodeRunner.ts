import { useCallback, useState } from 'react'
import type { TestCase } from '../../types/testCase'
import { toTestResult } from './compareOutput'
import { javascriptRunner } from './runners'
import type { FunctionTestResult, LogEntry } from './types'
import type { WorkerRunResult } from './workerClient'

export interface CodeRunOutcome {
  results: FunctionTestResult[]
  allPassed: boolean
  logs: LogEntry[]
  logsTruncated: boolean
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
  }
}

export function useCodeRunner() {
  const [running, setRunning] = useState(false)

  const run = useCallback(
    async (
      code: string,
      functionName: string,
      testSuite: TestCase[],
    ): Promise<CodeRunOutcome> => {
      setRunning(true)
      try {
        const result = await javascriptRunner.run({
          code,
          functionName,
          testSuite,
        })
        return toOutcome(testSuite, result, javascriptRunner.timeoutMs)
      } finally {
        setRunning(false)
      }
    },
    [],
  )

  return { run, running }
}
