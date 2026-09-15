import { useSyncExternalStore } from 'react'
import type { GenerationJob } from '../../lib/api'

const WATCHED_STORAGE_KEY = 'builp:watched-generation-jobs'

interface GenerationJobsState {
  jobs: GenerationJob[]
  pollRequest: number
}

let state: GenerationJobsState = { jobs: [], pollRequest: 0 }
const listeners = new Set<() => void>()

function setState(next: GenerationJobsState) {
  state = next
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function useGenerationJobs(): GenerationJobsState {
  return useSyncExternalStore(subscribe, () => state)
}

export function setGenerationJobs(jobs: GenerationJob[]) {
  setState({ ...state, jobs })
}

export function clearGenerationJobs() {
  if (state.jobs.length > 0) setGenerationJobs([])
}

// Jobs this browser saw while they ran. A toast shows when one of them
// finishes, also after a reload. Storage can fail, so it is best effort.
function readWatched(): Set<string> {
  try {
    const raw = localStorage.getItem(WATCHED_STORAGE_KEY)
    const ids: unknown = raw ? JSON.parse(raw) : []
    return new Set(Array.isArray(ids) ? ids.map(String) : [])
  } catch {
    return new Set()
  }
}

function writeWatched(ids: Set<string>) {
  try {
    localStorage.setItem(WATCHED_STORAGE_KEY, JSON.stringify([...ids]))
  } catch {
    // Ignore: the toast is a convenience
  }
}

export function isWatched(jobId: string) {
  return readWatched().has(jobId)
}

export function watchJobId(jobId: string) {
  const ids = readWatched()
  if (ids.has(jobId)) return
  ids.add(jobId)
  writeWatched(ids)
}

export function unwatchJobId(jobId: string) {
  const ids = readWatched()
  if (ids.delete(jobId)) writeWatched(ids)
}

export function hasWatchedJobs() {
  return readWatched().size > 0
}

export function keepOnlyWatched(jobIds: string[]) {
  const known = new Set(jobIds)
  const ids = readWatched()
  const kept = new Set([...ids].filter((id) => known.has(id)))
  if (kept.size !== ids.size) writeWatched(kept)
}

export function watchGenerationJob(job: GenerationJob) {
  watchJobId(job.id)
  setState({
    jobs: [job, ...state.jobs.filter((existing) => existing.id !== job.id)],
    pollRequest: state.pollRequest + 1,
  })
}
