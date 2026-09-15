import { WorkerClient } from './workerClient'

export const javascriptRunner = new WorkerClient(
  () =>
    new Worker(new URL('./js.worker.ts', import.meta.url), { type: 'module' }),
  3000,
)
