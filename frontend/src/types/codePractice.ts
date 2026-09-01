import type { TestCase } from './testCase'

export type CodePractice =
  | {
      type: 'function'
      id: string
      title: string
      functionSignature: string
      description: string
      testSuite: TestCase[]
    }
  | {
      type: 'component'
      id: string
      title: string
      starterFiles: Record<string, string>
      dependencies: Record<string, string>
    }
