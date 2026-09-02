import type { TestCase } from '../types/testCase'

export interface FunctionTestResult {
  testCase: TestCase
  actualOutput?: unknown
  passed: boolean
  error?: string
}

export interface FunctionTestRun {
  results: FunctionTestResult[]
  allPassed: boolean
}

export function runFunctionTests(
  code: string,
  functionName: string,
  testSuite: TestCase[],
): FunctionTestRun {
  let fn: (...args: unknown[]) => unknown

  try {
    // eslint-disable-next-line no-new-func
    fn = new Function(`${code}\nreturn ${functionName};`)()
  } catch (err) {
    const error = err instanceof Error ? err.message : 'Failed to parse code'
    const results = testSuite.map((testCase) => ({
      testCase,
      passed: false,
      error,
    }))
    return { results, allPassed: false }
  }

  const results = testSuite.map((testCase): FunctionTestResult => {
    try {
      const actualOutput = fn(...testCase.input)
      const passed =
        JSON.stringify(actualOutput) === JSON.stringify(testCase.expectedOutput)
      return { testCase, actualOutput, passed }
    } catch (err) {
      const error = err instanceof Error ? err.message : 'Runtime error'
      return { testCase, passed: false, error }
    }
  })

  return { results, allPassed: results.every((r) => r.passed) }
}
