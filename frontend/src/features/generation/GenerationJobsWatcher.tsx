import { useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Anchor } from '@mantine/core'
import { notifications } from '@mantine/notifications'
import {
  CheckCircleIcon,
  SignpostIcon,
  WarningCircleIcon,
} from '@phosphor-icons/react'
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

type FinishedLook = {
  color: string
  icon: React.ReactNode
  title: string
  linkText: string
}

function look(job: GenerationJob): FinishedLook {
  if (job.status === 'succeeded' && job.course_id) {
    return {
      color: 'green',
      icon: <CheckCircleIcon weight="fill" size={20} />,
      title: 'Your course is ready',
      linkText: `Open "${job.topic}"`,
    }
  }
  if (job.status === 'refused') {
    return {
      color: 'yellow',
      icon: <SignpostIcon weight="fill" size={20} />,
      title: 'This topic is not a fit',
      linkText: 'See why',
    }
  }
  return {
    color: 'red',
    icon: <WarningCircleIcon weight="fill" size={20} />,
    title: 'Course generation failed',
    linkText: 'See what went wrong',
  }
}

function showFinishedNotification(job: GenerationJob) {
  const id = `generation-job-${job.id}`
  const { color, icon, title, linkText } = look(job)
  const to =
    job.status === 'succeeded' && job.course_id
      ? `/courses/${job.course_id}`
      : `/courses/generate/${job.id}`
  notifications.show({
    id,
    color,
    icon,
    title,
    autoClose: 15000,
    message: (
      <Anchor
        component={Link}
        to={to}
        size="sm"
        onClick={() => notifications.hide(id)}
      >
        {linkText}
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
