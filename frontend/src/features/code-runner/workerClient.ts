import type {
  LogEntry,
  RawTestResult,
  RunRequest,
  SetupError,
  WorkerMessage,
} from './types'

export type WorkerRunResult = {
  logs: LogEntry[]
  logsTruncated: boolean
} & (
  | { status: 'completed'; setupError?: SetupError; results: RawTestResult[] }
  | { status: 'timedOut' }
  | { status: 'crashed'; message: string }
)

export class WorkerClient {
  readonly timeoutMs: number
  private readonly createWorker: () => Worker
  private worker: Worker | null = null
  private nextId = 1
  private queue: Promise<unknown> = Promise.resolve()

  constructor(createWorker: () => Worker, timeoutMs: number) {
    this.createWorker = createWorker
    this.timeoutMs = timeoutMs
  }

  run(request: Omit<RunRequest, 'id'>): Promise<WorkerRunResult> {
    const next = this.queue.then(() => this.execute(request))
    this.queue = next.catch(() => {})
    return next
  }

  private execute(request: Omit<RunRequest, 'id'>): Promise<WorkerRunResult> {
    const worker = (this.worker ??= this.createWorker())
    const id = this.nextId++
    const logs: LogEntry[] = []
    let logsTruncated = false

    return new Promise((resolve) => {
      let timer: ReturnType<typeof setTimeout> | undefined

      const stopWorker = () => {
        worker.terminate()
        if (this.worker === worker) this.worker = null
      }

      const finish = (result: WorkerRunResult) => {
        clearTimeout(timer)
        worker.removeEventListener('message', onMessage)
        worker.removeEventListener('error', onError)
        resolve(result)
      }

      const onMessage = (event: MessageEvent<WorkerMessage>) => {
        const message = event.data
        if (message.id !== id) return
        switch (message.type) {
          case 'log':
            logs.push(message.entry)
            break
          case 'logsTruncated':
            logsTruncated = true
            break
          case 'result':
            finish({
              status: 'completed',
              setupError: message.setupError,
              results: message.results,
              logs,
              logsTruncated,
            })
            break
        }
      }

      const onError = (event: ErrorEvent) => {
        stopWorker()
        finish({
          status: 'crashed',
          message: event.message || 'The code runner stopped unexpectedly.',
          logs,
          logsTruncated,
        })
      }

      worker.addEventListener('message', onMessage)
      worker.addEventListener('error', onError)
      timer = setTimeout(() => {
        stopWorker()
        finish({ status: 'timedOut', logs, logsTruncated })
      }, this.timeoutMs)
      worker.postMessage({ id, ...request } satisfies RunRequest)
    })
  }
}
