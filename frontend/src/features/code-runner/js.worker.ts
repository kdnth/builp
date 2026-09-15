import { createLogSink, type LogSink } from './logSink'
import type {
  LogEntry,
  RawTestResult,
  RunRequest,
  WorkerMessage,
} from './types'

let sink: LogSink | null = null
let currentTestIndex: number | null = null

function post(message: WorkerMessage) {
  self.postMessage(message)
}

function formatArg(value: unknown): string {
  if (typeof value === 'string') return value
  if (typeof value === 'function')
    return `[Function ${value.name || 'anonymous'}]`
  if (value instanceof Error) return `${value.name}: ${value.message}`
  if (typeof value === 'object' && value !== null) {
    try {
      return JSON.stringify(value)
    } catch {
      return String(value)
    }
  }
  return String(value)
}

function write(stream: LogEntry['stream'], args: unknown[]) {
  sink?.write(stream, args.map(formatArg).join(' '), currentTestIndex)
}

Object.assign(console, {
  log: (...args: unknown[]) => write('stdout', args),
  info: (...args: unknown[]) => write('stdout', args),
  debug: (...args: unknown[]) => write('stdout', args),
  warn: (...args: unknown[]) => write('stderr', args),
  error: (...args: unknown[]) => write('stderr', args),
})

const SOURCE_URL = 'solution.js'

const FUNCTION_HEADER_LINES = 2

function errorMessage(err: unknown) {
  return err instanceof Error ? `${err.name}: ${err.message}` : String(err)
}

function errorLine(err: unknown, lineCount: number) {
  if (!(err instanceof Error) || !err.stack) return undefined
  const match = err.stack.match(/solution\.js:(\d+):\d+/)
  if (!match) return undefined
  const line = Number(match[1]) - FUNCTION_HEADER_LINES
  return line >= 1 && line <= lineCount ? line : undefined
}

function serializeOutput(value: unknown): RawTestResult {
  try {
    const json = JSON.stringify(value)
    return json === undefined ? {} : { outputJson: json }
  } catch {
    return { error: 'Return value is not JSON serializable' }
  }
}

self.addEventListener('message', (event: MessageEvent<RunRequest>) => {
  const { id, code, functionName, testSuite } = event.data
  sink = createLogSink(id, post)
  currentTestIndex = null

  const lineCount = code.split('\n').length

  let fn: unknown
  try {
    // eslint-disable-next-line no-new-func
    fn = new Function(
      `${code}\nreturn ${functionName};\n//# sourceURL=${SOURCE_URL}`,
    )()
  } catch (err) {
    post({
      type: 'result',
      id,
      setupError: {
        message: errorMessage(err),
        line: errorLine(err, lineCount),
      },
      results: [],
    })
    return
  }

  if (typeof fn !== 'function') {
    post({
      type: 'result',
      id,
      setupError: { message: `Define a function named \`${functionName}\`` },
      results: [],
    })
    return
  }

  const results = testSuite.map((testCase, index): RawTestResult => {
    currentTestIndex = index
    try {
      return serializeOutput(fn(...testCase.input))
    } catch (err) {
      return { error: errorMessage(err), line: errorLine(err, lineCount) }
    }
  })
  currentTestIndex = null

  post({ type: 'result', id, results })
})

post({ type: 'ready' })
