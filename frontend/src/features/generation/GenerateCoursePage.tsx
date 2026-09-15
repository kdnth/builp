import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Alert,
  Anchor,
  Button,
  Container,
  NumberInput,
  PasswordInput,
  Paper,
  Radio,
  SegmentedControl,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { MagicWandIcon, WarningCircleIcon } from '@phosphor-icons/react'
import {
  ApiError,
  createGenerationJob,
  type CreateGenerationJobInput,
  type GenerationMode,
} from '../../lib/api'
import { useAuthSession } from '../../lib/auth'
import type { CodeLanguage } from '../../types/codeLanguage'

interface Placeholders {
  topic: string
  audience: string
}

const PLACEHOLDERS: Record<CodeLanguage, Placeholders> = {
  javascript: {
    topic: 'JavaScript array methods (map, filter, reduce)',
    audience: 'Developers who know basic JS but not functional array methods',
  },
  python: {
    topic: 'Python dictionaries and list comprehensions',
    audience: 'Beginners who know Python variables, loops, and functions',
  },
}

export default function GenerateCoursePage() {
  const navigate = useNavigate()
  const session = useAuthSession()
  const [topic, setTopic] = useState('')
  const [audience, setAudience] = useState('')
  const [numUnits, setNumUnits] = useState(3)
  const [lessonsPerUnit, setLessonsPerUnit] = useState(3)
  const [language, setLanguage] = useState<CodeLanguage>('javascript')
  const [generationMode, setGenerationMode] = useState<GenerationMode>('free_credit')
  const [providerApiKey, setProviderApiKey] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const baseInput = {
        topic,
        audience,
        num_units: numUnits,
        lessons_per_unit: lessonsPerUnit,
        language,
      }

      let input: CreateGenerationJobInput
      if (generationMode === 'provider_api_key') {
        const trimmedKey = providerApiKey.trim()
        if (!trimmedKey) {
          setError('Enter your Anthropic API key.')
          setSubmitting(false)
          return
        }
        input = {
          ...baseInput,
          generation_mode: 'provider_api_key',
          provider: 'anthropic',
          provider_api_key: trimmedKey,
        }
      } else {
        input = {
          ...baseInput,
          generation_mode: 'free_credit',
        }
      }

      const job = await createGenerationJob(input)
      navigate(`/courses/generate/${job.id}`)
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : 'Could not start course generation. Try again.',
      )
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
            <Stack gap={4}>
              <Text size="sm" fw={500}>
                Programming language
              </Text>
              <SegmentedControl
                value={language}
                onChange={(value) => setLanguage(value as CodeLanguage)}
                data={[
                  { label: 'JavaScript', value: 'javascript' },
                  { label: 'Python', value: 'python' },
                ]}
              />
            </Stack>
            <TextInput
              label="Topic"
              placeholder={PLACEHOLDERS[language].topic}
              value={topic}
              onChange={(e) => setTopic(e.currentTarget.value)}
              required
            />
            <TextInput
              label="Audience"
              placeholder={PLACEHOLDERS[language].audience}
              value={audience}
              onChange={(e) => setAudience(e.currentTarget.value)}
              required
            />
            <Radio.Group
              label="Generation mode"
              description="Choose the daily free credit path or bring your own Anthropic API key."
              value={generationMode}
              onChange={(value) => {
                const nextMode = value as GenerationMode
                setGenerationMode(nextMode)
                if (nextMode === 'free_credit') {
                  setProviderApiKey('')
                }
              }}
            >
              <Stack gap={8} mt={6}>
                <Radio
                  value="free_credit"
                  label="Use my one free generation credit (rate-limited to once every 24 hours)."
                />
                <Radio
                  value="provider_api_key"
                  label="Use my own Anthropic API key (bypasses the daily free-credit limit)."
                />
              </Stack>
            </Radio.Group>
            {generationMode === 'provider_api_key' && (
              <PasswordInput
                label="Anthropic API key"
                placeholder="Paste your key"
                value={providerApiKey}
                onChange={(e) => setProviderApiKey(e.currentTarget.value)}
                required
              />
            )}
            <Alert radius="md" color="blue">
              If you use your own API key, it is held in memory for this
              generation request only and is never written to the database or logs.
            </Alert>
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
              {generationMode === 'free_credit'
                ? 'Generate with free credit'
                : 'Generate with my API key'}
            </Button>
          </Stack>
        </form>
      </Paper>
    </Container>
  )
}
