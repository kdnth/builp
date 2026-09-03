import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Alert,
  Anchor,
  Button,
  Container,
  NumberInput,
  Paper,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { MagicWandIcon, WarningCircleIcon } from '@phosphor-icons/react'
import { createGenerationJob } from '../../lib/api'
import { useAuthSession } from '../../lib/auth'

export default function GenerateCoursePage() {
  const navigate = useNavigate()
  const session = useAuthSession()
  const [topic, setTopic] = useState('')
  const [audience, setAudience] = useState('')
  const [numUnits, setNumUnits] = useState(3)
  const [lessonsPerUnit, setLessonsPerUnit] = useState(3)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const job = await createGenerationJob({
        topic,
        audience,
        num_units: numUnits,
        lessons_per_unit: lessonsPerUnit,
      })
      navigate(`/courses/generate/${job.id}`)
    } catch {
      setError('Could not start course generation. Try again.')
    } finally {
      setSubmitting(false)
    }
  }

  if (!session.isPending && !session.data) {
    return (
      <Container size="xs" py="xl">
        <Paper withBorder radius="md" p="lg">
          <Stack gap="md">
            <Title order={2}>Generate a course</Title>
            <Text c="dimmed" size="sm">
              Sign in to generate a course with AI.
            </Text>
            <Button component={Link} to="/sign-in">
              Sign in
            </Button>
          </Stack>
        </Paper>
      </Container>
    )
  }

  return (
    <Container size="xs" py="xl">
      <Paper withBorder radius="md" p="lg">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Stack gap={4}>
              <Anchor component={Link} to="/" size="sm">
                ← All courses
              </Anchor>
              <Title order={2}>Generate a course</Title>
              <Text c="dimmed" size="sm">
                Describe a topic and audience. This writes a full course:
                lessons, code practice, and interactive activities. It takes
                a minute or two.
              </Text>
            </Stack>
            <TextInput
              label="Topic"
              placeholder="JavaScript array methods (map, filter, reduce)"
              value={topic}
              onChange={(e) => setTopic(e.currentTarget.value)}
              required
            />
            <TextInput
              label="Audience"
              placeholder="Developers who know basic JS but not functional array methods"
              value={audience}
              onChange={(e) => setAudience(e.currentTarget.value)}
              required
            />
            <NumberInput
              label="Units"
              min={1}
              max={10}
              value={numUnits}
              onChange={(value) => setNumUnits(typeof value === 'number' ? value : 1)}
            />
            <NumberInput
              label="Lessons per unit"
              min={1}
              max={8}
              value={lessonsPerUnit}
              onChange={(value) =>
                setLessonsPerUnit(typeof value === 'number' ? value : 1)
              }
            />
            {error && (
              <Alert color="red" icon={<WarningCircleIcon weight="fill" />} radius="md">
                {error}
              </Alert>
            )}
            <Button
              type="submit"
              loading={submitting}
              leftSection={<MagicWandIcon size={16} />}
            >
              Generate course
            </Button>
          </Stack>
        </form>
      </Paper>
    </Container>
  )
}
