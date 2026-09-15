import type { PyodideInterface } from 'pyodide'
import harness from './pythonHarness.py?raw'
import { createLogSink, type LogSink } from './logSink'
import type {
  LogEntry,
  RawTestResult,
  RunRequest,
  SetupError,
  WorkerMessage,
} from './types'

const PYODIDE_VERSION = '314.0.7'
const PYODIDE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`

type HarnessFunction = (...args: string[]) => string | undefined

let sink: LogSink | null = null
let currentTestIndex: number | null = null

function post(message: WorkerMessage) {
  self.postMessage(message)
}

function errorMessage(err: unknown) {
  return err instanceof Error ? err.message : String(err)
}

async function loadHarness() {
  const { loadPyodide } = (await import(
    /* @vite-ignore */ `${PYODIDE_URL}pyodide.mjs`
  )) as { loadPyodide: typeof import('pyodide').loadPyodide }
  const pyodide: PyodideInterface = await loadPyodide({ indexURL: PYODIDE_URL })
  pyodide.registerJsModule('_runner_io', {
    write: (stream: LogEntry['stream'], text: string) =>
      sink?.write(stream, text, currentTestIndex),
  })
  pyodide.runPython(harness)
  return {
    loadSolution: pyodide.globals.get('load_solution') as HarnessFunction,
    runTest: pyodide.globals.get('run_test') as HarnessFunction,
  }
}

function runRequest(
  { id, code, functionName, testSuite }: RunRequest,
  { loadSolution, runTest }: Awaited<ReturnType<typeof loadHarness>>,
) {
  sink = createLogSink(id, post)
  currentTestIndex = null

  try {
    const setupJson = loadSolution(code, functionName)
    if (setupJson) {
      const setupError = JSON.parse(setupJson) as SetupError
      post({ type: 'result', id, setupError, results: [] })
      return
    }

    const results = testSuite.map((testCase, index): RawTestResult => {
      currentTestIndex = index
      return JSON.parse(runTest(JSON.stringify(testCase.input))!)
    })
    currentTestIndex = null
    post({ type: 'result', id, results })
  } catch (err) {
    post({
      type: 'result',
      id,
      setupError: { message: `Python stopped: ${errorMessage(err)}` },
      results: [],
      fatal: true,
    })
  }
}

const harnessReady = loadHarness()

harnessReady.then(
  (functions) => {
    self.addEventListener('message', (event: MessageEvent<RunRequest>) =>
      runRequest(event.data, functions),
    )
    post({ type: 'ready' })
  },
  (err) => {
    post({
      type: 'loadFailed',
      message: `Python failed to load: ${errorMessage(err)}`,
    })
  },
)
