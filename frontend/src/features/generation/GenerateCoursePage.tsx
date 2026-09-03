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
  Select,
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
  type SupportedGenerationProvider,
} from '../../lib/api'
import { useAuthSession } from '../../lib/auth'

const PROVIDER_OPTIONS: Array<{ value: SupportedGenerationProvider; label: string }> = [
  { value: 'anthropic', label: 'Anthropic' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'groq', label: 'Groq' },
  { value: 'xai', label: 'xAI' },
  { value: 'mistral', label: 'Mistral' },
  { value: 'gemini', label: 'Gemini' },
  { value: 'ollama', label: 'Ollama' },
  { value: 'deepseek', label: 'DeepSeek' },
]

export default function GenerateCoursePage() {
  const navigate = useNavigate()
  const session = useAuthSession()
  const [topic, setTopic] = useState('')
  const [audience, setAudience] = useState('')
  const [numUnits, setNumUnits] = useState(3)
  const [lessonsPerUnit, setLessonsPerUnit] = useState(3)
  const [generationMode, setGenerationMode] = useState<GenerationMode>('free_credit')
  const [provider, setProvider] = useState<SupportedGenerationProvider | null>(null)
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
      }

      let input: CreateGenerationJobInput
      if (generationMode === 'provider_api_key') {
        if (!provider) {
          setError('Pick a provider before generating with your own API key.')
          setSubmitting(false)
          return
        }
        const trimmedKey = providerApiKey.trim()
        if (!trimmedKey) {
          setError('Enter your provider API key.')
          setSubmitting(false)
          return
        }
        input = {
          ...baseInput,
          generation_mode: 'provider_api_key',
          provider,
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
            <Radio.Group
              label="Generation mode"
              description="Choose the daily free credit path or bring your own provider key."
              value={generationMode}
              onChange={(value) => {
                const nextMode = value as GenerationMode
                setGenerationMode(nextMode)
                if (nextMode === 'free_credit') {
                  setProvider(null)
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
                  label="Use my own provider API key (bypasses the daily free-credit limit)."
                />
              </Stack>
            </Radio.Group>
            {generationMode === 'provider_api_key' && (
              <Stack gap="xs">
                <Select
                  label="Provider"
                  placeholder="Pick a provider"
                  data={PROVIDER_OPTIONS}
                  value={provider}
                  onChange={(value) =>
                    setProvider((value as SupportedGenerationProvider | null) ?? null)
                  }
                  required
                />
                <PasswordInput
                  label="Provider API key"
                  placeholder={
                    provider === 'ollama'
                      ? "If your Ollama server has no auth, use 'ollama'"
                      : 'Paste your key'
                  }
                  value={providerApiKey}
                  onChange={(e) => setProviderApiKey(e.currentTarget.value)}
                  required
                />
              </Stack>
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
