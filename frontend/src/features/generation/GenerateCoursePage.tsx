import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  Alert,
  Anchor,
  Button,
  Collapse,
  Container,
  NumberInput,
  PasswordInput,
  Paper,
  Radio,
  SegmentedControl,
  Select,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
} from '@mantine/core'
import { MagicWandIcon, WarningCircleIcon } from '@phosphor-icons/react'
import {
  ApiError,
  createGenerationJob,
  type CodePracticeChoice,
  type CreateGenerationJobInput,
  type GenerationJob,
  type GenerationMode,
  type LearnerLevel,
} from '../../lib/api'
import type { CourseType } from '../../types/course'
import { useAuthSession } from '../../lib/auth'
import { watchGenerationJob } from './generationJobsStore'

interface Placeholders {
  topic: string
  audience: string
}

const PLACEHOLDERS: Record<string, Placeholders> = {
  javascript: {
    topic: 'JavaScript array methods (map, filter, reduce)',
    audience: 'Developers who know basic JS but not functional array methods',
  },
  python: {
    topic: 'Python dictionaries and list comprehensions',
    audience: 'Beginners who know Python variables, loops, and functions',
  },
  general: {
    topic: 'How supply and demand set prices',
    audience: 'Students with no economics background',
  },
}

export default function GenerateCoursePage() {
  const navigate = useNavigate()
  const session = useAuthSession()
  // A refused job sends the learner back here with their request filled in.
  const previous = (useLocation().state as { job?: GenerationJob } | null)?.job
  const [topic, setTopic] = useState(previous?.topic ?? '')
  const [audience, setAudience] = useState(previous?.audience ?? '')
  const [numUnits, setNumUnits] = useState(previous?.num_units ?? 3)
  const [lessonsPerUnit, setLessonsPerUnit] = useState(
    previous?.lessons_per_unit ?? 3,
  )
  const [courseType, setCourseType] = useState<CourseType>(
    previous?.course_type ?? 'programming',
  )
  const [language, setLanguage] = useState<CodePracticeChoice>(
    previous?.language ?? 'javascript',
  )
  const [learningGoals, setLearningGoals] = useState(
    previous?.learning_goals ?? '',
  )
  const [level, setLevel] = useState<LearnerLevel>(
    previous?.level ?? 'beginner',
  )
  const [notes, setNotes] = useState(previous?.notes ?? '')
  const [moreOptionsOpen, setMoreOptionsOpen] = useState(false)
  const [generationMode, setGenerationMode] =
    useState<GenerationMode>('free_credit')
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
        course_type: courseType,
        language,
        learning_goals: learningGoals.trim() || null,
        level,
        notes: notes.trim() || null,
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
      watchGenerationJob(job)
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

  const placeholders =
    courseType === 'general'
      ? PLACEHOLDERS.general
      : (PLACEHOLDERS[language] ?? PLACEHOLDERS.javascript)

  return (
    <Container size="xs" py="xl">
      <Paper withBorder radius="md" p="lg">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Stack gap={4}>
              <Anchor component={Link} to="/" size="sm">
                ← My courses
              </Anchor>
              <Title order={2}>Generate a course</Title>
              <Text c="dimmed" size="sm">
                Describe a topic and audience. This writes a full course:
                lessons, practice, and interactive activities. It takes a minute
                or two.
              </Text>
            </Stack>
            <Stack gap={4}>
              <Text size="sm" fw={500}>
                Course type
              </Text>
              <SegmentedControl
                value={courseType}
                onChange={(value) => {
                  const nextType = value as CourseType
                  setCourseType(nextType)
                  setLanguage(
                    nextType === 'programming' ? 'javascript' : 'auto',
                  )
                }}
                data={[
                  { label: 'Programming', value: 'programming' },
                  { label: 'Other subject', value: 'general' },
                ]}
              />
            </Stack>
            {courseType === 'programming' ? (
              <Stack gap={4}>
                <Text size="sm" fw={500}>
                  Programming language
                </Text>
                <SegmentedControl
                  value={language}
                  onChange={(value) => setLanguage(value as CodePracticeChoice)}
                  data={[
                    { label: 'JavaScript', value: 'javascript' },
                    { label: 'Python', value: 'python' },
                  ]}
                />
              </Stack>
            ) : (
              <Select
                label="Code practice"
                description="Some subjects, such as statistics, are easier to practice with code."
                value={language}
                onChange={(value) =>
                  setLanguage((value as CodePracticeChoice) ?? 'auto')
                }
                allowDeselect={false}
                data={[
                  { label: 'Let the model decide', value: 'auto' },
                  { label: 'No code practice', value: 'none' },
                  { label: 'Python', value: 'python' },
                  { label: 'JavaScript', value: 'javascript' },
                ]}
              />
            )}
            <TextInput
              label="Topic"
              placeholder={placeholders.topic}
              value={topic}
              onChange={(e) => setTopic(e.currentTarget.value)}
              required
            />
            <TextInput
              label="Audience"
              placeholder={placeholders.audience}
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
              generation request only and is never written to the database or
              logs.
            </Alert>
            <Anchor
              component="button"
              type="button"
              size="sm"
              onClick={() => setMoreOptionsOpen((open) => !open)}
            >
              {moreOptionsOpen ? 'Fewer options' : 'More options'}
            </Anchor>
            <Collapse expanded={moreOptionsOpen}>
              <Stack gap="md">
                <Select
                  label="Level"
                  value={level}
                  onChange={(value) =>
                    setLevel((value as LearnerLevel) ?? 'beginner')
                  }
                  allowDeselect={false}
                  data={[
                    { label: 'Beginner', value: 'beginner' },
                    { label: 'Intermediate', value: 'intermediate' },
                    { label: 'Advanced', value: 'advanced' },
                  ]}
                />
                <Textarea
                  label="Learning goals"
                  description="What should a learner be able to do at the end?"
                  placeholder="Read a supply and demand chart and explain a price change"
                  autosize
                  minRows={2}
                  maxLength={1000}
                  value={learningGoals}
                  onChange={(e) => setLearningGoals(e.currentTarget.value)}
                />
                <Textarea
                  label="Anything to include or avoid"
                  placeholder="Use UK spelling. Skip the maths derivations."
                  autosize
                  minRows={2}
                  maxLength={1000}
                  value={notes}
                  onChange={(e) => setNotes(e.currentTarget.value)}
                />
              </Stack>
            </Collapse>
            <NumberInput
              label="Units"
              min={1}
              max={10}
              value={numUnits}
              onChange={(value) =>
                setNumUnits(typeof value === 'number' ? value : 1)
              }
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
              <Alert
                color="red"
                icon={<WarningCircleIcon weight="fill" />}
                radius="md"
              >
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
