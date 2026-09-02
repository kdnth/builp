import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import type { Course } from '../../types/course'
import { Anchor, Box, Container, Paper, Stack, Stepper, Title } from '@mantine/core'
import { CheckCircleIcon, LockIcon } from '@phosphor-icons/react'
import LessonComponent from './LessonComponent'
import { isLessonComplete, isLessonUnlocked } from '../../helpers/progress'

interface UnitComponentProps {
  course: Course
  unitIndex: number
  completedLessonIds: Set<string>
  markLessonComplete: (lessonId: string) => void
}

export default function UnitComponent({
  course,
  unitIndex,
  completedLessonIds,
  markLessonComplete,
}: UnitComponentProps) {
  const unit = course.units[unitIndex]
  const navigate = useNavigate()

  const [activeLessonIndex, setActiveLessonIndex] = useState(() => {
    const firstIncomplete = unit.lessons.findIndex(
      (lesson) => !isLessonComplete(completedLessonIds, lesson.id),
    )
    return firstIncomplete === -1 ? unit.lessons.length - 1 : firstIncomplete
  })

  const nextUnit = course.units[unitIndex + 1]
  const isLastLessonInUnit = activeLessonIndex === unit.lessons.length - 1
  const isFinalLesson = isLastLessonInUnit && !nextUnit

  function handleStepClick(index: number) {
    if (isLessonUnlocked(completedLessonIds, unit, index)) {
      setActiveLessonIndex(index)
    }
  }

  function goToNextLesson() {
    setActiveLessonIndex((current) =>
      current < unit.lessons.length - 1 ? current + 1 : current,
    )
  }

  function goToNextUnit() {
    if (nextUnit) {
      navigate(`/courses/${course.id}/units/${nextUnit.id}`)
    }
  }

  const nextAction = isLastLessonInUnit
    ? nextUnit
      ? { label: `Next Unit: ${nextUnit.title}`, onClick: goToNextUnit }
      : null
    : {
        label: `Next Lesson: ${unit.lessons[activeLessonIndex + 1].title}`,
        onClick: goToNextLesson,
      }

  return (
    <Container size="lg" py="xl">
      <Stack gap="lg">
        <Stack gap={4}>
          <Anchor component={Link} to={`/courses/${course.id}`} size="sm">
            ← {course.title}
          </Anchor>
          <Title order={1}>{unit.title}</Title>
        </Stack>
        <Paper withBorder radius="md" p="lg" shadow="sm">
          <Stepper active={activeLessonIndex} onStepClick={handleStepClick}>
            {unit.lessons.map((lesson, index) => {
              const unlocked = isLessonUnlocked(completedLessonIds, unit, index)
              const complete = isLessonComplete(completedLessonIds, lesson.id)
              return (
                <Stepper.Step
                  key={lesson.id}
                  label={lesson.title}
                  allowStepSelect={unlocked}
                  icon={unlocked ? undefined : <LockIcon size={16} />}
                  completedIcon={<CheckCircleIcon weight="fill" />}
                  color={complete ? 'green' : undefined}
                >
                  <Box mt="md">
                    <LessonComponent
                      key={lesson.id}
                      lesson={lesson}
                      onComplete={() => markLessonComplete(lesson.id)}
                      nextAction={nextAction}
                      isFinalLesson={isFinalLesson}
                    />
                  </Box>
                </Stepper.Step>
              )
            })}
          </Stepper>
        </Paper>
      </Stack>
    </Container>
  )
}
