import { useState } from 'react'
import {
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
} from '@mantine/core'
import { Link, Navigate, useParams } from 'react-router-dom'
import { CheckCircleIcon, CircleIcon, LockIcon, TagIcon } from '@phosphor-icons/react'
import { useCourse } from '../../hooks/useCourse'
import { useCourseProgress } from '../../hooks/useCourseProgress'
import { useAuthSession } from '../../lib/auth'
import { updateCourseTags } from '../../lib/api'
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
  const dirty = JSON.stringify([...draft].sort()) !== JSON.stringify([...tags].sort())

  async function handleSave() {
    setSaving(true)
    try {
      const result = await updateCourseTags(courseId, draft)
      onSaved(result.tags)
      setDraft(result.tags)
    } catch {
      // leave the draft as-is so the user can retry
    } finally {
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

export default function CourseTreePage() {
  const { courseId } = useParams<{ courseId: string }>()
  const { course, setCourse, loading, notFound } = useCourse(courseId)
  const session = useAuthSession()
  const { completedLessonIds } = useCourseProgress(courseId ?? '')

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

  const completed = countCompletedLessons(completedLessonIds, course)
  const total = countTotalLessons(course)
  const percent = total === 0 ? 0 : Math.round((completed / total) * 100)

  return (
    <Container size="lg" py="xl">
      <Stack gap="lg">
        <Stack gap={4}>
          <Anchor component={Link} to="/" size="sm">
            ← All courses
          </Anchor>
          <Group justify="space-between" align="center">
            <Title order={1}>{course.title}</Title>
            <Badge color={percent === 100 ? 'green' : 'gray'} variant="light">
              {completed}/{total} lessons
            </Badge>
          </Group>
          <Progress value={percent} radius="xl" />
        </Stack>

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

        <Stack gap="sm">
          {course.units.map((unit, unitIndex) => {
            const unlocked = isUnitUnlocked(completedLessonIds, course, unitIndex)
            const complete = isUnitComplete(completedLessonIds, unit)
            const completedInUnit = unit.lessons.filter((lesson) =>
              isLessonComplete(completedLessonIds, lesson.id),
            ).length

            const label = unit.title
            const description = unlocked
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
