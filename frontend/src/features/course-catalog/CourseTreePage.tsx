import { useEffect, useState } from 'react'
import {
  Alert,
  Anchor,
  Badge,
  Button,
  Card,
  Center,
  Group,
  Container,
  Loader,
  NavLink,
  Progress,
  Stack,
  Text,
  TagsInput,
  Title,
  ActionIcon,
} from '@mantine/core'
import { Link, Navigate, useParams } from 'react-router-dom'
import {
  BookmarkSimpleIcon,
  CheckCircleIcon,
  CircleIcon,
  LockIcon,
  QuestionIcon,
  TagIcon,
  WarningIcon,
} from '@phosphor-icons/react'
import { useCourse } from '../../hooks/useCourse'
import { useCourseProgressContext } from '../../hooks/CourseProgressContext'
import { useAuthSession } from '../../lib/auth'
import {
  ApiError,
  saveCourse,
  unsaveCourse,
  updateCourseTags,
} from '../../lib/api'
import UnsaveCourseModal from './UnsaveCourseModal'
import ReportCourseModal from '../feedback/ReportCourseModal'
import { downloadCourseJson } from '../../lib/downloadCourseJson'
import { hasCompletedTour, useTour } from '../tour/TourContext'
import type { TourStep } from '../tour/TourContext'
import {
  countCompletedLessons,
  countTotalLessons,
  isLessonComplete,
  isUnitComplete,
  isUnitUnlocked,
} from '../../helpers/progress'

function TagEditor({
  courseId,
  tags,
  onSaved,
}: {
  courseId: string
  tags: string[]
  onSaved: (tags: string[]) => void
}) {
  const [draft, setDraft] = useState(tags)
  const [saving, setSaving] = useState(false)
  const dirty =
    JSON.stringify([...draft].sort()) !== JSON.stringify([...tags].sort())

  async function handleSave() {
    setSaving(true)
    try {
      const result = await updateCourseTags(courseId, draft)
      onSaved(result.tags)
      setDraft(result.tags)
    } catch {
      setSaving(false)
    }
  }

  return (
    <Group align="flex-end" gap="xs">
      <TagsInput
        label="Tags"
        placeholder="Add a tag"
        value={draft}
        onChange={setDraft}
        style={{ flex: 1 }}
        leftSection={<TagIcon size={16} />}
      />
      <Button size="sm" disabled={!dirty} loading={saving} onClick={handleSave}>
        Save
      </Button>
    </Group>
  )
}

const COURSE_TREE_TOUR_ID = 'course-tree'

const courseTreeTourSteps: TourStep[] = [
  {
    target: '[data-tour="course-progress"]',
    title: 'Track your progress',
    content: 'This bar fills in as you complete lessons across the course.',
  },
  {
    target: '[data-tour="course-tags"]',
    title: 'Organize with tags',
    content: 'Add tags to help you find this course again from the catalog.',
  },
  {
    target: '[data-tour="course-units"]',
    title: 'Work through units in order',
    content:
      'Units unlock as you finish the ones before them. Locked units show a lock icon.',
  },
  {
    target: '[data-tour="course-download"]',
    title: 'Take it offline',
    content:
      'Download the full course as JSON any time you want a local copy to edit or reupload.',
  },
]

export default function CourseTreePage() {
  const { courseId } = useParams<{ courseId: string }>()
  const { course, setCourse, loading, notFound } = useCourse(courseId)
  const session = useAuthSession()
  const { completedLessonIds, resetProgress } = useCourseProgressContext()
  const { start } = useTour()
  const [savingCourse, setSavingCourse] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [unsaveConfirmOpen, setUnsaveConfirmOpen] = useState(false)
  const [reportOpen, setReportOpen] = useState(false)

  useEffect(() => {
    if (!loading && course && !hasCompletedTour(COURSE_TREE_TOUR_ID)) {
      start(COURSE_TREE_TOUR_ID, courseTreeTourSteps)
    }
  }, [loading, course, start])

  async function handleSaveCourse() {
    if (!course) return
    setSaveError(null)
    setSavingCourse(true)
    try {
      await saveCourse(course.id)
      setCourse({ ...course, saved: true })
    } catch (err) {
      setSaveError(
        err instanceof ApiError ? err.message : 'Could not save this course.',
      )
    } finally {
      setSavingCourse(false)
    }
  }

  async function handleUnsaveCourse() {
    if (!course) return
    setSaveError(null)
    setSavingCourse(true)
    try {
      await unsaveCourse(course.id)
      resetProgress()
      setCourse({ ...course, saved: false })
    } catch (err) {
      setSaveError(
        err instanceof ApiError ? err.message : 'Could not unsave this course.',
      )
    } finally {
      setSavingCourse(false)
      setUnsaveConfirmOpen(false)
    }
  }

  if (notFound) {
    return <Navigate to="/" replace />
  }

  if (loading || !course) {
    return (
      <Center py={80}>
        <Loader />
      </Center>
    )
  }

  const isOwner = session.data?.user.id === course.owner_user_id
  const isSignedIn = !session.isPending && session.data != null

  const completed = countCompletedLessons(completedLessonIds, course)
  const total = countTotalLessons(course)
  const percent = total === 0 ? 0 : Math.round((completed / total) * 100)

  return (
    <Container size="lg" py="xl">
      <Stack gap="lg">
        <Stack gap={4}>
          <Group justify="space-between">
            <Anchor component={Link} to="/" size="sm">
              ← My courses
            </Anchor>
            <Group gap="xs">
              {course.saved && !isOwner && (
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => setUnsaveConfirmOpen(true)}
                >
                  <BookmarkSimpleIcon size={16} weight="fill" />
                </Button>
              )}
              {isSignedIn && !isOwner && (
                <Button
                  size="sm"
                  variant="subtle"
                  color="gray"
                  leftSection={<WarningIcon size={16} />}
                  onClick={() => setReportOpen(true)}
                >
                  Report a problem
                </Button>
              )}
              <Button
                data-tour="course-download"
                size="sm"
                onClick={() => downloadCourseJson(course)}
              >
                Download course JSON
              </Button>
              <ActionIcon
                variant="light"
                radius="xl"
                size="lg"
                onClick={() => start(COURSE_TREE_TOUR_ID, courseTreeTourSteps)}
              >
                <QuestionIcon size={20} />
              </ActionIcon>
            </Group>
          </Group>
          <Group justify="space-between" align="center">
            <Title order={1}>{course.title}</Title>
            <Badge color={percent === 100 ? 'green' : 'gray'} variant="light">
              {completed}/{total} lessons
            </Badge>
          </Group>
          <Progress data-tour="course-progress" value={percent} radius="xl" />
        </Stack>

        {course.saved && saveError && (
          <Text size="sm" c="red">
            {saveError}
          </Text>
        )}

        <UnsaveCourseModal
          opened={unsaveConfirmOpen}
          courseTitle={course.title}
          working={savingCourse}
          onCancel={() => setUnsaveConfirmOpen(false)}
          onConfirm={() => void handleUnsaveCourse()}
        />

        <ReportCourseModal
          opened={reportOpen}
          onClose={() => setReportOpen(false)}
          courseId={course.id}
          courseTitle={course.title}
        />

        {!course.saved && (
          <Alert
            color="primary"
            variant="light"
            radius="md"
            icon={<BookmarkSimpleIcon size={20} />}
            title={
              isSignedIn
                ? 'Save this course to start learning'
                : 'Sign in to start learning'
            }
          >
            <Stack gap="sm" align="flex-start">
              <Text size="sm">
                {isSignedIn
                  ? 'Save the course to view lessons and track your progress.'
                  : 'Sign in and save the course to view lessons and track your progress.'}
              </Text>
              {isSignedIn ? (
                <Button
                  size="sm"
                  leftSection={<BookmarkSimpleIcon size={16} />}
                  loading={savingCourse}
                  onClick={() => void handleSaveCourse()}
                >
                  Save to My Courses
                </Button>
              ) : (
                <Button size="sm" component={Link} to="/sign-in">
                  Sign in
                </Button>
              )}
              {saveError && (
                <Text size="sm" c="red">
                  {saveError}
                </Text>
              )}
            </Stack>
          </Alert>
        )}

        <div data-tour="course-tags">
          {isOwner ? (
            <TagEditor
              courseId={course.id}
              tags={course.tags}
              onSaved={(tags) => setCourse({ ...course, tags })}
            />
          ) : course.tags.length > 0 ? (
            <Group gap="xs">
              {course.tags.map((tag) => (
                <Badge key={tag} variant="light" color="gray">
                  {tag}
                </Badge>
              ))}
            </Group>
          ) : null}
        </div>

        <Stack data-tour="course-units" gap="sm">
          {course.units.map((unit, unitIndex) => {
            const unlocked =
              course.saved &&
              isUnitUnlocked(completedLessonIds, course, unitIndex)
            const complete = isUnitComplete(completedLessonIds, unit)
            const completedInUnit = unit.lessons.filter((lesson) =>
              isLessonComplete(completedLessonIds, lesson.id),
            ).length

            const label = unit.title
            const description = !course.saved
              ? `${unit.lessons.length} lesson${unit.lessons.length === 1 ? '' : 's'}`
              : unlocked
                ? `${completedInUnit}/${unit.lessons.length} lessons complete`
                : 'Complete prerequisites to start unit'
            const leftSection = complete ? (
              <CheckCircleIcon
                size={20}
                color="var(--mantine-color-green-6)"
                weight="fill"
              />
            ) : unlocked ? (
              <CircleIcon size={20} />
            ) : (
              <LockIcon size={20} />
            )

            return (
              <Card key={unit.id} withBorder radius="md" p={0}>
                {unlocked ? (
                  <NavLink
                    component={Link}
                    to={`/courses/${course.id}/units/${unit.id}`}
                    variant="filled"
                    label={label}
                    description={description}
                    leftSection={leftSection}
                  />
                ) : (
                  <NavLink
                    disabled
                    variant="filled"
                    label={label}
                    description={description}
                    leftSection={leftSection}
                  />
                )}
                <Stack gap={4} pl={54} pr="md" pb="sm">
                  {unit.lessons.map((lesson) => {
                    const lessonComplete = isLessonComplete(
                      completedLessonIds,
                      lesson.id,
                    )
                    return (
                      <Group key={lesson.id} gap="xs">
                        {lessonComplete ? (
                          <CheckCircleIcon
                            size={14}
                            color="var(--mantine-color-green-6)"
                            weight="fill"
                          />
                        ) : unlocked ? (
                          <CircleIcon size={14} />
                        ) : (
                          <LockIcon size={14} />
                        )}
                        <Text size="sm" c={unlocked ? undefined : 'dimmed'}>
                          {lesson.title}
                        </Text>
                      </Group>
                    )
                  })}
                </Stack>
              </Card>
            )
          })}
        </Stack>
      </Stack>
    </Container>
  )
}
