import type { TestCase } from '../../types/testCase'
import type { FunctionTestResult, RawTestResult } from './types'

export function outputMatches(actual: unknown, expected: unknown): boolean {
  return JSON.stringify(actual) === JSON.stringify(expected)
}

export function toTestResult(
  testCase: TestCase,
  raw: RawTestResult,
): FunctionTestResult {
  if (raw.error !== undefined) {
    return { testCase, passed: false, error: raw.error }
  }
  const actualOutput =
    raw.outputJson === undefined ? undefined : JSON.parse(raw.outputJson)
  return {
    testCase,
    actualOutput,
    passed: outputMatches(actualOutput, testCase.expectedOutput),
  }
}
