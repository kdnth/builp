import { useEffect, useState } from 'react'
import {
  ActionIcon,
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Code,
  Container,
  Group,
  List,
  Modal,
  Progress,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { Link } from 'react-router-dom'
import {
  DownloadIcon,
  GraduationCapIcon,
  MagicWandIcon,
  MagnifyingGlassIcon,
  TrashIcon,
  UploadIcon,
  WarningCircleIcon,
  XIcon,
} from '@phosphor-icons/react'
import {
  ApiError,
  deleteCourse,
  getCourseFromApi,
  type CourseSummary,
} from '../../lib/api'
import { downloadCourseJson } from '../../lib/downloadCourseJson'
import { useCourses } from '../../hooks/useCourses'
import { useCourseProgress } from '../../hooks/useCourseProgress'

type DeleteStep = 'closed' | 'confirm' | 'download-prompt'

function CourseCard({
  course,
  onTagClick,
  onDeleted,
}: {
  course: CourseSummary
  onTagClick: (tag: string) => void
  onDeleted: () => void
}) {
  const { completedLessonIds } = useCourseProgress(course.id)
  const completed = completedLessonIds.size
  const total = course.lesson_count
  const percent = total === 0 ? 0 : Math.round((completed / total) * 100)
  const [issues, setIssues] = useState<string[] | null>(null)
  const [deleteStep, setDeleteStep] = useState<DeleteStep>('closed')
  const [working, setWorking] = useState(false)

  async function handleDelete(options: { download: boolean }) {
    setIssues(null)
    setWorking(true)
    try {
      if (options.download) {
        const fullCourse = await getCourseFromApi(course.id)
        downloadCourseJson(fullCourse)
      }
      await deleteCourse(course.id)
      setDeleteStep('closed')
      onDeleted()
    } catch (err) {
      setIssues([
        err instanceof ApiError ? err.message : 'Could not delete this course.',
      ])
    } finally {
      setWorking(false)
    }
  }

  return (
    <Card withBorder radius="md" p="lg">
      <Stack gap="sm">
        <Anchor
          component={Link}
          to={`/courses/${course.id}`}
          underline="never"
          c="inherit"
        >
          <Group gap="xs">
            <GraduationCapIcon size={20} />
            <Title order={4}>{course.title}</Title>
          </Group>
        </Anchor>
        <Text c="dimmed" size="sm">
          {course.unit_count} unit{course.unit_count === 1 ? '' : 's'} · {total}{' '}
          lesson{total === 1 ? '' : 's'}
        </Text>
        {course.tags.length > 0 && (
          <Group gap={4}>
            {course.tags.map((tag) => (
              <Badge
                key={tag}
                variant="light"
                color="gray"
                style={{ cursor: 'pointer' }}
                onClick={() => onTagClick(tag)}
              >
                {tag}
              </Badge>
            ))}
          </Group>
        )}
        <Stack gap={4}>
          <Progress value={percent} radius="xl" />
          <Text size="xs" c="dimmed">
            {completed}/{total} lessons complete
          </Text>
        </Stack>
        <Group justify="end">
          <ActionIcon
            variant="transparent"
            aria-label="Delete Course"
            onClick={() => setDeleteStep('confirm')}
            color="gray"
          >
            <TrashIcon size={20} />
          </ActionIcon>
        </Group>
        {issues && (
          <Alert
            color="red"
            icon={<WarningCircleIcon weight="fill" />}
            radius="md"
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

      <Modal
        opened={deleteStep === 'confirm'}
        onClose={() => setDeleteStep('closed')}
        title="Delete course?"
        centered
      >
        <Stack gap="md">
          <Text size="sm">
            Are you sure you want to delete "{course.title}"?
          </Text>
          <Group justify="end">
            <Button variant="default" onClick={() => setDeleteStep('closed')}>
              Cancel
            </Button>
            <Button color="red" onClick={() => setDeleteStep('download-prompt')}>
              Continue
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={deleteStep === 'download-prompt'}
        onClose={() => setDeleteStep('closed')}
        title="Download before deleting?"
        centered
      >
        <Stack gap="md">
          <Text size="sm">
            You will not be able to restore this course from the app. Would
            you like to download the course as a JSON file to upload later?
          </Text>
          <Group justify="end">
            <Button
              variant="default"
              disabled={working}
              onClick={() => setDeleteStep('closed')}
            >
              Cancel
            </Button>
            <Button
              variant="default"
              loading={working}
              onClick={() => handleDelete({ download: false })}
            >
              Delete without downloading
            </Button>
            <Button
              color="red"
              leftSection={<DownloadIcon size={16} />}
              loading={working}
              onClick={() => handleDelete({ download: true })}
            >
              Download and delete
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Card>
  )
}

export default function CourseListPage() {
  const [searchInput, setSearchInput] = useState('')
  const [q, setQ] = useState('')
  const [tag, setTag] = useState<string | null>(null)
  const { courses, loading, refetch } = useCourses({ q, tag: tag ?? undefined })

  useEffect(() => {
    const timeout = setTimeout(() => setQ(searchInput), 300)
    return () => clearTimeout(timeout)
  }, [searchInput])

  return (
    <Container size="lg" py="xl">
      <Stack gap="lg">
        <Group justify="space-between" align="center">
          <Title order={1}>Courses</Title>
          <Group gap="sm">
            <Button
              component={Link}
              to="/courses/generate"
              leftSection={<MagicWandIcon size={16} />}
            >
              Generate Course
            </Button>
            <Button
              component={Link}
              to="/courses/new"
              variant="default"
              leftSection={<UploadIcon size={16} />}
            >
              Upload Course
            </Button>
          </Group>
        </Group>

        <Group gap="sm">
          <TextInput
            placeholder="Search courses"
            value={searchInput}
            onChange={(e) => setSearchInput(e.currentTarget.value)}
            leftSection={<MagnifyingGlassIcon size={16} />}
            style={{ flex: 1 }}
          />
          {tag && (
            <Badge
              size="lg"
              variant="filled"
              rightSection={
                <XIcon
                  size={12}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setTag(null)}
                />
              }
            >
              {tag}
            </Badge>
          )}
        </Group>

        {!loading && courses.length === 0 && (
          <Text c="dimmed" size="sm">
            No courses found.
          </Text>
        )}

        <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}>
          {courses.map((course) => (
            <CourseCard
              key={course.id}
              course={course}
              onTagClick={setTag}
              onDeleted={refetch}
            />
          ))}
        </SimpleGrid>
      </Stack>
    </Container>
  )
}
