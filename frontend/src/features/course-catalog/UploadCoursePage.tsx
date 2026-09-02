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
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { BracketsCurlyIcon, UploadIcon, WarningCircleIcon } from '@phosphor-icons/react'
import { courseSchema } from '../../schemas/course'
import { useCourses } from '../../hooks/useCourses'
import { findCourse } from '../../helpers/findCourse'
import CourseSchemaModal from './CourseSchemaModal'

export default function UploadCoursePage() {
  const navigate = useNavigate()
  const { courses, addCourse } = useCourses()
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

    if (findCourse(courses, result.data.id)) {
      setIssues([
        `A course with id "${result.data.id}" already exists. Change the "id" field and try again.`,
      ])
      return
    }

    addCourse(result.data)
    navigate(`/courses/${result.data.id}`)
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
            Upload a course JSON file.
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
