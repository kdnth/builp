import { useEffect, useState } from 'react'
import {
  Anchor,
  Badge,
  Button,
  Card,
  Container,
  Group,
  Progress,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { Link } from 'react-router-dom'
import {
  GraduationCapIcon,
  MagicWandIcon,
  MagnifyingGlassIcon,
  UploadIcon,
  XIcon,
} from '@phosphor-icons/react'
import type { CourseSummary } from '../../lib/api'
import { useCourses } from '../../hooks/useCourses'
import { useCourseProgress } from '../../hooks/useCourseProgress'

function CourseCard({
  course,
  onTagClick,
}: {
  course: CourseSummary
  onTagClick: (tag: string) => void
}) {
  const { completedLessonIds } = useCourseProgress(course.id)
  const completed = completedLessonIds.size
  const total = course.lesson_count
  const percent = total === 0 ? 0 : Math.round((completed / total) * 100)

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
          {course.unit_count} unit{course.unit_count === 1 ? '' : 's'} ·{' '}
          {total} lesson{total === 1 ? '' : 's'}
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
      </Stack>
    </Card>
  )
}

export default function CourseListPage() {
  const [searchInput, setSearchInput] = useState('')
  const [q, setQ] = useState('')
  const [tag, setTag] = useState<string | null>(null)
  const { courses, loading } = useCourses({ q, tag: tag ?? undefined })

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
            <CourseCard key={course.id} course={course} onTagClick={setTag} />
          ))}
        </SimpleGrid>
      </Stack>
    </Container>
  )
}
