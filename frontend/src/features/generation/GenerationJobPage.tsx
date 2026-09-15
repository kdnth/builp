import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  Alert,
  Button,
  Container,
  Loader,
  Paper,
  Progress,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { WarningCircleIcon } from '@phosphor-icons/react'
import { ApiError, getGenerationJob, type GenerationJob } from '../../lib/api'
import { unwatchJobId } from './generationJobsStore'
import {
  lessonProgressText,
  progressLabel,
  progressPercent,
} from './generationProgress'

const POLL_INTERVAL_MS = 2000

export default function GenerationJobPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const navigate = useNavigate()
  const [job, setJob] = useState<GenerationJob | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!jobId) return

    let cancelled = false
    let timeoutId: ReturnType<typeof setTimeout>

    async function poll() {
      try {
        const latest = await getGenerationJob(jobId as string)
        if (cancelled) return
        setJob(latest)

        if (latest.status === 'pending' || latest.status === 'running') {
          timeoutId = setTimeout(poll, POLL_INTERVAL_MS)
          return
        }

        unwatchJobId(latest.id)

        if (latest.status === 'succeeded') {
          if (!latest.course_id) {
            setError('The course finished generating but has no id. Try again.')
            return
          }
          // The course already exists in the shared catalog as soon as the
          // job succeeds, so there's nothing left to do here but go look
          // at it. CourseTreePage fetches it itself.
          navigate(`/courses/${latest.course_id}`)
        }
      } catch (err) {
        if (cancelled) return
        setError(
          err instanceof ApiError
            ? err.message
            : 'Could not check generation status.',
        )
      }
    }

    poll()

    return () => {
      cancelled = true
      clearTimeout(timeoutId)
    }
  }, [jobId, navigate])

  if (error) {
    return (
      <Container size="xs" py="xl">
        <Alert
          color="red"
          icon={<WarningCircleIcon weight="fill" />}
          radius="md"
          title="Error"
        >
          {error}
        </Alert>
      </Container>
    )
  }

  if (job?.status === 'failed') {
    return (
      <Container size="xs" py="xl">
        <Paper withBorder radius="md" p="lg">
          <Stack gap="md">
            <Title order={2}>Generation failed</Title>
            <Alert
              color="red"
              icon={<WarningCircleIcon weight="fill" />}
              radius="md"
            >
              {job.error ?? 'Unknown error.'}
            </Alert>
            <Button component={Link} to="/courses/generate">
              Try again
            </Button>
          </Stack>
        </Paper>
      </Container>
    )
  }

  const lessonText = job ? lessonProgressText(job) : null

  return (
    <Container size="xs" py="xl">
      <Paper withBorder radius="md" p="lg">
        <Stack gap="md" align="center" ta="center">
          <Loader />
          <Title order={2}>
            {job ? `${progressLabel(job)}...` : 'Starting...'}
          </Title>
          <Text c="dimmed" size="sm">
            {job?.topic ?? 'Setting things up...'}
          </Text>
          <Stack gap={6} w="100%">
            <Progress
              value={job ? progressPercent(job) : 0}
              animated
              aria-label="Generation progress"
            />
            {lessonText && (
              <Text size="sm" c="dimmed">
                {lessonText}
              </Text>
            )}
          </Stack>
          <Text c="dimmed" size="xs">
            This usually takes a minute or two. You can leave this page: the
            header shows progress, and a notification appears when the course is
            ready.
          </Text>
        </Stack>
      </Paper>
    </Container>
  )
}
