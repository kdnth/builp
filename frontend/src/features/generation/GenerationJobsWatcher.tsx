import { useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Anchor } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import { CheckCircleIcon, WarningCircleIcon } from '@phosphor-icons/react'
import { listGenerationJobs, type GenerationJob } from '../../lib/api'
import { useAuthSession } from '../../lib/auth'
import {
  clearGenerationJobs,
  hasWatchedJobs,
  isWatched,
  keepOnlyWatched,
  setGenerationJobs,
  unwatchJobId,
  useGenerationJobs,
  watchJobId,
} from './generationJobsStore'
import { isActiveJob } from './generationProgress'

const POLL_INTERVAL_MS = 3000
const ERROR_RETRY_MS = 15000

function showFinishedNotification(job: GenerationJob) {
  const id = `generation-job-${job.id}`
  const succeeded = job.status === 'succeeded' && job.course_id
  notifications.show({
    id,
    color: succeeded ? 'green' : 'red',
    icon: succeeded ? (
      <CheckCircleIcon weight="fill" size={20} />
    ) : (
      <WarningCircleIcon weight="fill" size={20} />
    ),
    title: succeeded ? 'Your course is ready' : 'Course generation failed',
    autoClose: 15000,
    message: (
      <Anchor
        component={Link}
        to={
          succeeded
            ? `/courses/${job.course_id}`
            : `/courses/generate/${job.id}`
        }
        size="sm"
        onClick={() => notifications.hide(id)}
      >
        {succeeded ? `Open "${job.topic}"` : 'See what went wrong'}
      </Anchor>
    ),
  })
}

export default function GenerationJobsWatcher() {
  const session = useAuthSession()
  const signedIn = !session.isPending && session.data !== null
  const { jobs, pollRequest } = useGenerationJobs()
  const { pathname } = useLocation()
  const pathnameRef = useRef(pathname)

  useEffect(() => {
    pathnameRef.current = pathname
  }, [pathname])

  useEffect(() => {
    if (!signedIn) {
      clearGenerationJobs()
      return
    }

    let cancelled = false
    let timeoutId: ReturnType<typeof setTimeout> | undefined

    async function poll() {
      try {
        const latest = await listGenerationJobs()
        if (cancelled) return
        setGenerationJobs(latest)
        keepOnlyWatched(latest.map((job) => job.id))
        if (latest.some(isActiveJob)) {
          timeoutId = setTimeout(poll, POLL_INTERVAL_MS)
        }
      } catch {
        if (!cancelled && hasWatchedJobs()) {
          timeoutId = setTimeout(poll, ERROR_RETRY_MS)
        }
      }
    }

    void poll()
    return () => {
      cancelled = true
      clearTimeout(timeoutId)
    }
  }, [signedIn, pollRequest])

  useEffect(() => {
    for (const job of jobs) {
      if (isActiveJob(job)) {
        watchJobId(job.id)
        continue
      }
      if (!isWatched(job.id)) continue
      unwatchJobId(job.id)
      if (pathnameRef.current !== `/courses/generate/${job.id}`) {
        showFinishedNotification(job)
      }
    }
  }, [jobs])

  return null
}
