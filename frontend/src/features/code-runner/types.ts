import type { TestCase } from '../../types/testCase'

export interface RunRequest {
  id: number
  code: string
  functionName: string
  testSuite: TestCase[]
}

export interface LogEntry {
  stream: 'stdout' | 'stderr'
  text: string
  testIndex: number | null
}

export interface SetupError {
  message: string
  line?: number
}

export interface RawTestResult {
  outputJson?: string
  error?: string
}

export type WorkerMessage =
  | { type: 'log'; id: number; entry: LogEntry }
  | { type: 'logsTruncated'; id: number }
  | {
      type: 'result'
      id: number
      setupError?: SetupError
      results: RawTestResult[]
    }

export interface FunctionTestResult {
  testCase: TestCase
  actualOutput?: unknown
  passed: boolean
  error?: string
}
