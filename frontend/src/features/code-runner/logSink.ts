import type { LogEntry, WorkerMessage } from './types'

const MAX_LINES = 1000
const MAX_CHARS = 100_000

export interface LogSink {
  write: (
    stream: LogEntry['stream'],
    text: string,
    testIndex: number | null,
  ) => void
}

export function createLogSink(
  runId: number,
  post: (message: WorkerMessage) => void,
): LogSink {
  let lines = 0
  let chars = 0
  let truncated = false

  function truncate() {
    truncated = true
    post({ type: 'logsTruncated', id: runId })
  }

  return {
    write(stream, text, testIndex) {
      if (truncated) return
      if (lines >= MAX_LINES || chars >= MAX_CHARS) {
        truncate()
        return
      }
      const kept = text.slice(0, MAX_CHARS - chars)
      lines += 1
      chars += kept.length
      post({ type: 'log', id: runId, entry: { stream, text: kept, testIndex } })
      if (kept.length < text.length) truncate()
    },
  }
}
