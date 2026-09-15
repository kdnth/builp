import type { CodeLanguage } from '../../types/codeLanguage'
import { WorkerClient } from './workerClient'

const javascriptRunner = new WorkerClient({
  createWorker: () =>
    new Worker(new URL('./js.worker.ts', import.meta.url), { type: 'module' }),
  timeoutMs: 3000,
  loadTimeoutMs: 10_000,
})

const pythonRunner = new WorkerClient({
  createWorker: () =>
    new Worker(new URL('./python.worker.ts', import.meta.url), {
      type: 'module',
    }),
  timeoutMs: 5000,
  loadTimeoutMs: 60_000,
})

export const runners: Record<CodeLanguage, WorkerClient> = {
  javascript: javascriptRunner,
  python: pythonRunner,
}
