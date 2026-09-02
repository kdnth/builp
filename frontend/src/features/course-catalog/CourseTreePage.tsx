import {
  Anchor,
  Badge,
  Card,
  Group,
  Container,
  NavLink,
  Progress,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { Link, Navigate, useParams } from 'react-router-dom'
import { CheckCircleIcon, CircleIcon, LockIcon } from '@phosphor-icons/react'
import { getCourse } from '../../data/courses'
import { useCourseProgress } from '../../hooks/useCourseProgress'
import {
  countCompletedLessons,
  countTotalLessons,
  isLessonComplete,
  isUnitComplete,
  isUnitUnlocked,
} from '../../helpers/progress'

export default function CourseTreePage() {
  const { courseId } = useParams<{ courseId: string }>()
  const course = courseId ? getCourse(courseId) : undefined
  const { completedLessonIds } = useCourseProgress(courseId ?? '')

  if (!course) {
    return <Navigate to="/" replace />
  }

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

        <Stack gap="sm">
          {course.units.map((unit, unitIndex) => {
            const unlocked = isUnitUnlocked(completedLessonIds, course, unitIndex)
            const complete = isUnitComplete(completedLessonIds, unit)
            const completedInUnit = unit.lessons.filter((lesson) =>
              isLessonComplete(completedLessonIds, lesson.id),
            ).length

            return (
              <Card key={unit.id} withBorder radius="md" p={0}>
                <NavLink
                  component={unlocked ? Link : 'div'}
                  to={
                    unlocked ? `/courses/${course.id}/units/${unit.id}` : undefined
                  }
                  disabled={!unlocked}
                  variant="filled"
                  label={unit.title}
                  description={
                    unlocked
                      ? `${completedInUnit}/${unit.lessons.length} lessons complete`
                      : 'Locked — complete the previous unit first'
                  }
                  leftSection={
                    complete ? (
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
                  }
                />
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
