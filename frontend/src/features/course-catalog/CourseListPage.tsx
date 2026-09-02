import {
  Button,
  Card,
  Container,
  Group,
  Progress,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { Link } from 'react-router-dom'
import { GraduationCapIcon, UploadIcon } from '@phosphor-icons/react'
import type { Course } from '../../types/course'
import { useCourses } from '../../hooks/useCourses'
import { useCourseProgress } from '../../hooks/useCourseProgress'
import { countCompletedLessons, countTotalLessons } from '../../helpers/progress'

function CourseCard({ course }: { course: Course }) {
  const { completedLessonIds } = useCourseProgress(course.id)
  const completed = countCompletedLessons(completedLessonIds, course)
  const total = countTotalLessons(course)
  const percent = total === 0 ? 0 : Math.round((completed / total) * 100)

  return (
    <Card
      component={Link}
      to={`/courses/${course.id}`}
      withBorder
      radius="md"
      p="lg"
      style={{ textDecoration: 'none', color: 'inherit' }}
    >
      <Stack gap="sm">
        <Group gap="xs">
          <GraduationCapIcon size={20} />
          <Title order={4}>{course.title}</Title>
        </Group>
        <Text c="dimmed" size="sm">
          {course.units.length} unit{course.units.length === 1 ? '' : 's'} ·{' '}
          {total} lesson{total === 1 ? '' : 's'}
        </Text>
        <Stack gap={4}>
          <Progress value={percent} radius="xl" />
          <Text size="xs" c="dimmed">
            {completed}/{total} lessons complete
          </Text>
        </Stack>
      </Stack>
    </Card>
  )
}

export default function CourseListPage() {
  const { courses } = useCourses()

  return (
    <Container size="lg" py="xl">
      <Stack gap="lg">
        <Group justify="space-between" align="center">
          <Title order={1}>Courses</Title>
          <Button
            component={Link}
            to="/courses/new"
            leftSection={<UploadIcon size={16} />}
          >
            Upload Course
          </Button>
        </Group>
        <SimpleGrid cols={{ base: 1, sm: 2, md: 3 }}>
          {courses.map((course) => (
            <CourseCard key={course.id} course={course} />
          ))}
        </SimpleGrid>
      </Stack>
    </Container>
  )
}
