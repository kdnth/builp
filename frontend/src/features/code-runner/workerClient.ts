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

export interface RunnerState {
  status: 'idle' | 'loading' | 'ready' | 'failed'
  restarting: boolean
  error?: string
}

interface WorkerClientOptions {
  createWorker: () => Worker
  timeoutMs: number
  loadTimeoutMs: number
}

export class WorkerClient {
  readonly timeoutMs: number
  private readonly createWorker: () => Worker
  private readonly loadTimeoutMs: number
  private worker: Promise<Worker> | null = null
  private loadCount = 0
  private state: RunnerState = { status: 'idle', restarting: false }
  private readonly listeners = new Set<() => void>()
  private nextId = 1
  private queue: Promise<unknown> = Promise.resolve()

  constructor(options: WorkerClientOptions) {
    this.createWorker = options.createWorker
    this.timeoutMs = options.timeoutMs
    this.loadTimeoutMs = options.loadTimeoutMs
  }

  getState = (): RunnerState => this.state

  subscribe = (listener: () => void) => {
    this.listeners.add(listener)
    return () => {
      this.listeners.delete(listener)
    }
  }

  start(): Promise<Worker> {
    if (this.worker) return this.worker

    const worker = this.createWorker()
    this.setState({ status: 'loading', restarting: this.loadCount > 0 })

    const ready = new Promise<Worker>((resolve, reject) => {
      let timer: ReturnType<typeof setTimeout> | undefined

      const cleanup = () => {
        clearTimeout(timer)
        worker.removeEventListener('message', onMessage)
        worker.removeEventListener('error', onError)
      }

      const fail = (message: string) => {
        cleanup()
        this.discard(worker, ready)
        this.setState({ status: 'failed', restarting: false, error: message })
        reject(new Error(message))
      }

      const onMessage = (event: MessageEvent<WorkerMessage>) => {
        if (event.data.type === 'ready') {
          cleanup()
          this.loadCount += 1
          this.setState({ status: 'ready', restarting: false })
          resolve(worker)
        } else if (event.data.type === 'loadFailed') {
          fail(event.data.message)
        }
      }

      const onError = (event: ErrorEvent) => {
        fail(event.message || 'The code runner failed to start.')
      }

      worker.addEventListener('message', onMessage)
      worker.addEventListener('error', onError)
      timer = setTimeout(
        () => fail('The code runner took too long to start.'),
        this.loadTimeoutMs,
      )
    })

    ready.catch(() => {})
    this.worker = ready
    return ready
  }

  run(request: Omit<RunRequest, 'id'>): Promise<WorkerRunResult> {
    const next = this.queue.then(() => this.execute(request))
    this.queue = next.catch(() => {})
    return next
  }

  private setState(state: RunnerState) {
    this.state = state
    this.listeners.forEach((listener) => listener())
  }

  private discard(worker: Worker, ready: Promise<Worker>) {
    worker.terminate()
    if (this.worker === ready) {
      this.worker = null
      this.setState({ status: 'idle', restarting: false })
    }
  }

  private restart(worker: Worker, ready: Promise<Worker>) {
    this.discard(worker, ready)
    void this.start()
  }

  private async execute(
    request: Omit<RunRequest, 'id'>,
  ): Promise<WorkerRunResult> {
    let ready: Promise<Worker>
    let worker: Worker
    try {
      ready = this.start()
      worker = await ready
    } catch (err) {
      return {
        status: 'crashed',
        message: err instanceof Error ? err.message : String(err),
        logs: [],
        logsTruncated: false,
      }
    }

    const id = this.nextId++
    const logs: LogEntry[] = []
    let logsTruncated = false

    return new Promise((resolve) => {
      let timer: ReturnType<typeof setTimeout> | undefined

      const finish = (result: WorkerRunResult) => {
        clearTimeout(timer)
        worker.removeEventListener('message', onMessage)
        worker.removeEventListener('error', onError)
        resolve(result)
      }

      const onMessage = (event: MessageEvent<WorkerMessage>) => {
        const message = event.data
        switch (message.type) {
          case 'log':
            if (message.id === id) logs.push(message.entry)
            break
          case 'logsTruncated':
            if (message.id === id) logsTruncated = true
            break
          case 'result':
            if (message.id !== id) break
            if (message.fatal) this.restart(worker, ready)
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
        this.restart(worker, ready)
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
        this.restart(worker, ready)
        finish({ status: 'timedOut', logs, logsTruncated })
      }, this.timeoutMs)
      worker.postMessage({ id, ...request } satisfies RunRequest)
    })
  }
}
