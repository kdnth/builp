import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Alert,
  Anchor,
  Button,
  Code,
  Container,
  FileInput,
  Group,
  List,
  Paper,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { BracketsCurlyIcon, UploadIcon, WarningCircleIcon } from '@phosphor-icons/react'
import { courseSchema } from '../../schemas/course'
import { ApiError, createCourseOnApi } from '../../lib/api'
import { useAuthSession } from '../../lib/auth'
import CourseSchemaModal from './CourseSchemaModal'

export default function UploadCoursePage() {
  const navigate = useNavigate()
  const session = useAuthSession()
  const [fileName, setFileName] = useState<string | null>(null)
  const [issues, setIssues] = useState<string[] | null>(null)
  const [schemaOpened, { open: openSchema, close: closeSchema }] =
    useDisclosure(false)

  async function handleFile(file: File | null) {
    setIssues(null)
    setFileName(file?.name ?? null)
    if (!file) return

    let text: string
    try {
      text = await file.text()
    } catch {
      setIssues(['Could not read the file.'])
      return
    }

    let parsed: unknown
    try {
      parsed = JSON.parse(text)
    } catch (err) {
      setIssues([
        `Not valid JSON: ${err instanceof Error ? err.message : 'parse error'}`,
      ])
      return
    }

    const result = courseSchema.safeParse(parsed)
    if (!result.success) {
      setIssues(
        result.error.issues.map(
          (issue) => `${issue.path.join('.') || '(root)'}: ${issue.message}`,
        ),
      )
      return
    }

    try {
      const created = await createCourseOnApi(result.data)
      navigate(`/courses/${created.id}`)
    } catch (err) {
      setIssues([
        err instanceof ApiError ? err.message : 'Could not upload this course.',
      ])
    }
  }

  if (!session.isPending && !session.data) {
    return (
      <Container size="xs" py="xl">
        <Paper withBorder radius="md" p="lg">
          <Stack gap="md">
            <Title order={2}>Upload Course</Title>
            <Text c="dimmed" size="sm">
              Sign in to upload a course. Uploaded courses are attributed to
              you and visible to everyone.
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
    <Container size="sm" py="xl">
      <Stack gap="lg">
        <Stack gap={4}>
          <Anchor component={Link} to="/" size="sm">
            ← All courses
          </Anchor>
          <Title order={1}>Upload Course</Title>
          <Text c="dimmed" size="sm">
            Upload a course JSON file. It's attributed to you and visible to
            everyone.
          </Text>
        </Stack>

        <Group justify="space-between" align="flex-end">
          <FileInput
            label="Course JSON file"
            placeholder="Choose file..."
            accept="application/json"
            leftSection={<UploadIcon size={16} />}
            onChange={handleFile}
            style={{ flex: 1 }}
          />
          <Button
            variant="default"
            leftSection={<BracketsCurlyIcon size={16} />}
            onClick={openSchema}
          >
            View schema
          </Button>
        </Group>

        <CourseSchemaModal opened={schemaOpened} onClose={closeSchema} />

        {issues && (
          <Alert
            color="red"
            icon={<WarningCircleIcon weight="fill" />}
            radius="md"
            title={
              fileName ? `${fileName} failed validation` : 'Validation failed'
            }
          >
            <List size="sm" spacing={4}>
              {issues.map((issue, idx) => (
                <List.Item key={idx}>
                  <Code>{issue}</Code>
                </List.Item>
              ))}
            </List>
          </Alert>
        )}
      </Stack>
    </Container>
  )
}
