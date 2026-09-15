import { Link } from 'react-router-dom'
import { Button, Loader, Menu, Stack, Text, Tooltip } from '@mantine/core'
import { useGenerationJobs } from './generationJobsStore'
import {
  isActiveJob,
  progressLabel,
  shortProgressLabel,
} from './generationProgress'

export default function GenerationJobIndicator() {
  const { jobs } = useGenerationJobs()
  const active = jobs.filter(isActiveJob)

  if (active.length === 0) return null

  if (active.length === 1) {
    const job = active[0]
    return (
      <Tooltip label={`${job.topic}: ${progressLabel(job)}`}>
        <Button
          component={Link}
          to={`/courses/generate/${job.id}`}
          variant="light"
          size="xs"
          leftSection={<Loader size={12} />}
          aria-label={`Generating ${job.topic}: ${progressLabel(job)}`}
        >
          {shortProgressLabel(job)}
        </Button>
      </Tooltip>
    )
  }

  return (
    <Menu position="bottom-end" width={260}>
      <Menu.Target>
        <Button variant="light" size="xs" leftSection={<Loader size={12} />}>
          {active.length} generating
        </Button>
      </Menu.Target>
      <Menu.Dropdown>
        {active.map((job) => (
          <Menu.Item
            key={job.id}
            component={Link}
            to={`/courses/generate/${job.id}`}
          >
            <Stack gap={0}>
              <Text size="sm" lineClamp={1}>
                {job.topic}
              </Text>
              <Text size="xs" c="dimmed">
                {shortProgressLabel(job)}
              </Text>
            </Stack>
          </Menu.Item>
        ))}
      </Menu.Dropdown>
    </Menu>
  )
}
