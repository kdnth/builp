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
  SegmentedControl,
  Pagination,
  Progress,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  TextInput,
  Title,
  Tooltip,
} from '@mantine/core'
import { Link } from 'react-router-dom'
import {
  BookmarkSimpleIcon,
  DownloadIcon,
  GraduationCapIcon,
  MagicWandIcon,
  MagnifyingGlassIcon,
  QuestionIcon,
  TrashIcon,
  UploadIcon,
  WarningCircleIcon,
  XIcon,
} from '@phosphor-icons/react'
import {
  ApiError,
  deleteCourse,
  getCourseFromApi,
  saveCourse,
  unsaveCourse,
  type CourseSummary,
} from '../../lib/api'
import { downloadCourseJson } from '../../lib/downloadCourseJson'
import { useCourses } from '../../hooks/useCourses'
import { useCourseProgress } from '../../hooks/useCourseProgress'
import { useAuthSession } from '../../lib/auth'
import { hasCompletedTour, useTour, type TourStep } from '../tour/TourContext'
import UnsaveCourseModal from './UnsaveCourseModal'
import type { CourseType } from '../../types/course'

type DeleteStep = 'closed' | 'confirm' | 'download-prompt'

function CourseCard({
  course,
  currentUserId,
  showSaveButton,
  onTagClick,
  onDeleted,
}: {
  course: CourseSummary
  currentUserId: string | undefined
  showSaveButton: boolean
  onTagClick: (tag: string) => void
  onDeleted: () => void
}) {
  const isOwner = course.owner_user_id === currentUserId
  const { completedLessonIds, resetProgress } = useCourseProgress(course.id)
  const completed = completedLessonIds.size
  const total = course.lesson_count
  const percent = total === 0 ? 0 : Math.round((completed / total) * 100)
  const [issues, setIssues] = useState<string[] | null>(null)
  const [deleteStep, setDeleteStep] = useState<DeleteStep>('closed')
  const [working, setWorking] = useState(false)
  const [saved, setSaved] = useState(course.saved)
  const [saveWorking, setSaveWorking] = useState(false)
  const [unsaveConfirmOpen, setUnsaveConfirmOpen] = useState(false)

  useEffect(() => {
    setSaved(course.saved)
  }, [course.saved])

  async function handleToggleSave() {
    setSaveWorking(true)
    try {
      if (saved) {
        await unsaveCourse(course.id)
        setSaved(false)
        setUnsaveConfirmOpen(false)
        resetProgress()
      } else {
        await saveCourse(course.id)
        setSaved(true)
      }
    } catch (err) {
      setUnsaveConfirmOpen(false)
      setIssues([
        err instanceof ApiError
          ? err.message
          : 'Could not update saved status.',
      ])
    } finally {
      setSaveWorking(false)
    }
  }

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
        {(showSaveButton || isOwner) && (
          <Group justify="end" gap="xs">
            {showSaveButton && isOwner && (
              <Tooltip label="You own this course">
                <ActionIcon variant="transparent" color="gray" disabled>
                  <BookmarkSimpleIcon size={20} weight="fill" />
                </ActionIcon>
              </Tooltip>
            )}
            {showSaveButton && !isOwner && (
              <ActionIcon
                variant="transparent"
                color="gray"
                aria-label={saved ? 'Remove' : 'Save'}
                onClick={() =>
                  saved ? setUnsaveConfirmOpen(true) : void handleToggleSave()
                }
                disabled={saveWorking}
              >
                <BookmarkSimpleIcon
                  size={20}
                  weight={saved ? 'fill' : 'regular'}
                />
              </ActionIcon>
            )}
            {isOwner && (
              <ActionIcon
                variant="transparent"
                aria-label="Delete Course"
                onClick={() => setDeleteStep('confirm')}
                color="gray"
              >
                <TrashIcon size={20} />
              </ActionIcon>
            )}
          </Group>
        )}
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

      <UnsaveCourseModal
        opened={unsaveConfirmOpen}
        courseTitle={course.title}
        working={saveWorking}
        onCancel={() => setUnsaveConfirmOpen(false)}
        onConfirm={() => void handleToggleSave()}
      />

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
            <Button
              color="red"
              onClick={() => setDeleteStep('download-prompt')}
            >
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
            You will not be able to restore this course from the app. Would you
            like to download the course as a JSON file to upload later?
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

function CourseCardSkeleton() {
  return (
    <Card withBorder radius="md" p="lg">
      <Stack gap="sm">
        <Group gap="xs">
          <Skeleton height={20} width={20} circle />
          <Skeleton height={20} width="60%" />
        </Group>
        <Skeleton height={14} width="40%" />
        <Skeleton height={8} radius="xl" />
        <Skeleton height={12} width="30%" />
      </Stack>
    </Card>
  )
}

const COURSE_LIST_TOUR_ID = 'course-list'

const courseListTourSteps: TourStep[] = [
  {
    target: '[data-tour="course-grid"]',
    title: 'Look through your courses',
    content: 'This page contains all courses saved to your account.',
  },
  {
    target: '[data-tour="course-detail"]',
    title: 'View course details',
    content: 'Click on a course to see your progress and its details',
  },
  {
    target: '[data-tour="search-course-list"]',
    title: 'Search courses',
    content:
      'Use this search bar to search for specific courses by title. You can also click on course tags to filter the list for that tag.',
  },
  {
    target: '[data-tour="course-upload"]',
    title: 'Upload Course JSON',
    content:
      'Have your own course JSON file? Upload it here. This is a good option if you want to create your own courses without using the onboard generator - just make sure to use the schema!',
  },
  {
    target: '[data-tour="course-generate"]',
    title: 'Generate Course',
    content:
      'Use this button to generate a course based on a topic, audience, and a selected number of units and lessons. Generate once a day for free, or bring your own Anthropic API key.',
  },
]

const PAGE_SIZE = 24

export function CourseCatalog({ scope }: { scope: 'mine' | 'explore' }) {
  const [searchInput, setSearchInput] = useState('')
  const [q, setQ] = useState('')
  const [tag, setTag] = useState<string | null>(null)
  const [courseType, setCourseType] = useState<CourseType | 'all'>('all')
  const [page, setPage] = useState(1)
  const session = useAuthSession()
  const userId = session.data?.user.id
  const { courses, total, loading, refetch } = useCourses({
    q,
    tag: tag ?? undefined,
    courseType: courseType === 'all' ? undefined : courseType,
    forUserId: scope === 'mine' ? userId : undefined,
    limit: PAGE_SIZE,
    offset: (page - 1) * PAGE_SIZE,
  })
  const { start } = useTour()
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE))

  useEffect(() => {
    if (
      scope === 'mine' &&
      !loading &&
      !hasCompletedTour(COURSE_LIST_TOUR_ID)
    ) {
      start(COURSE_LIST_TOUR_ID, courseListTourSteps)
    }
  }, [scope, loading, start])

  useEffect(() => {
    const timeout = setTimeout(() => setQ(searchInput), 300)
    return () => clearTimeout(timeout)
  }, [searchInput])

  useEffect(() => {
    setPage(1)
  }, [q, tag, courseType, scope])

  return (
    <Container size="lg" py="xl">
      <Stack gap="lg">
        <Group justify="space-between" align="center">
          <Title order={1}>{scope === 'mine' ? 'My Courses' : 'Explore'}</Title>
          <Group gap="sm">
            {scope === 'mine' && (
              <>
                <Button
                  data-tour="course-generate"
                  component={Link}
                  to="/courses/generate"
                  leftSection={<MagicWandIcon size={16} />}
                >
                  Generate Course
                </Button>
                <Button
                  data-tour="course-upload"
                  component={Link}
                  to="/courses/new"
                  variant="default"
                  leftSection={<UploadIcon size={16} />}
                >
                  Upload Course
                </Button>
                <ActionIcon
                  variant="light"
                  radius="xl"
                  size="lg"
                  onClick={() =>
                    start(COURSE_LIST_TOUR_ID, courseListTourSteps)
                  }
                >
                  <QuestionIcon size={20} />
                </ActionIcon>
              </>
            )}
          </Group>
        </Group>

        <Group gap="sm">
          <TextInput
            data-tour="search-course-list"
            placeholder="Search courses"
            value={searchInput}
            onChange={(e) => setSearchInput(e.currentTarget.value)}
            leftSection={<MagnifyingGlassIcon size={16} />}
            style={{ flex: 1 }}
          />
          <SegmentedControl
            value={courseType}
            onChange={(value) => setCourseType(value as CourseType | 'all')}
            aria-label="Filter by course type"
            data={[
              { label: 'All', value: 'all' },
              { label: 'Programming', value: 'programming' },
              { label: 'Other subjects', value: 'general' },
            ]}
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

        <div data-tour="course-grid">
          {loading && (
            <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}>
              {Array.from({ length: 6 }, (_, idx) => (
                <CourseCardSkeleton key={idx} />
              ))}
            </SimpleGrid>
          )}

          {!loading && courses.length === 0 && (
            <Text c="dimmed" size="sm">
              {scope === 'mine'
                ? 'No courses found. Upload or generate one to get started.'
                : 'No courses found.'}
            </Text>
          )}

          {!loading && courses.length > 0 && (
            <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}>
              {courses.map((course) => (
                <CourseCard
                  data-tour="course-detail"
                  key={course.id}
                  course={course}
                  currentUserId={userId}
                  showSaveButton={scope === 'explore'}
                  onTagClick={setTag}
                  onDeleted={refetch}
                />
              ))}
            </SimpleGrid>
          )}
        </div>

        {!loading && pageCount > 1 && (
          <Group justify="center">
            <Pagination value={page} onChange={setPage} total={pageCount} />
          </Group>
        )}
      </Stack>
    </Container>
  )
}

export default function CourseListPage() {
  return <CourseCatalog scope="mine" />
}
