import { useEffect, useState } from 'react'
import type { Lesson } from '../../types/lesson'
import { Box, Button, Group, Paper, Stack, Stepper, Title } from '@mantine/core'
import { ArrowRightIcon } from '@phosphor-icons/react'
import type { LessonView } from '../../types/lessonView'
import { isCodePractice, isWrittenLesson } from '../../helpers/typeGuards'
import LessonViewRenderer from './LessonViewRenderer'
import ActivityAlert from './ActivityAlert'

interface LessonNextAction {
  label: string
  onClick: () => void
}

interface LessonComponentProps {
  lesson: Lesson
  onComplete?: () => void
  nextAction?: LessonNextAction | null
  isFinalLesson?: boolean
}

export default function LessonComponent({
  lesson,
  onComplete,
  nextAction,
  isFinalLesson,
}: LessonComponentProps) {
  const pageCount =
    1 + lesson.codePractices.length + lesson.interactivePractices.length
  const [active, setActive] = useState(0)
  const nextStep = () =>
    setActive((current) => (current < pageCount ? current + 1 : current))
  const prevStep = () =>
    setActive((current) => (current > 0 ? current - 1 : current))

  useEffect(() => {
    if (active === pageCount) {
      onComplete?.()
    }
  }, [active, pageCount, onComplete])

  const pages: LessonView[] = [
    lesson.writtenLesson,
    ...lesson.codePractices,
    ...lesson.interactivePractices,
  ]

  function getViewTypeString(view: LessonView) {
    if (isWrittenLesson(view)) {
      return 'Written Lesson'
    } else if (isCodePractice(view)) {
      return 'Code Practice'
    } else {
      return 'Interactive Practice'
    }
  }

  return (
    <Stack gap="md" m={8} p={4}>
      <Title order={1}>{lesson.title}</Title>
      <Stepper active={active} onStepClick={setActive}>
        {pages.map((page) => (
          <Stepper.Step
            key={page.id}
            label={page.title}
            description={getViewTypeString(page)}
          >
            <Box mt="md">
              <LessonViewRenderer view={page} />
            </Box>
          </Stepper.Step>
        ))}
        <Stepper.Completed>
          <Paper withBorder radius="md" p="lg" mt="md" shadow="sm">
            <Stack gap="md">
              <ActivityAlert
                status="correct"
                message={
                  isFinalLesson
                    ? "You've completed the course! Great work."
                    : 'Lesson complete! Nice work.'
                }
              />
              {nextAction && (
                <Group justify="flex-end">
                  <Button
                    onClick={nextAction.onClick}
                    rightSection={<ArrowRightIcon size={16} />}
                  >
                    {nextAction.label}
                  </Button>
                </Group>
              )}
            </Stack>
          </Paper>
        </Stepper.Completed>
      </Stepper>
      <Group justify="flex-end">
        <Button variant="default" onClick={prevStep} disabled={active === 0}>
          Back
        </Button>
        <Button onClick={nextStep} disabled={active === pageCount}>
          Next step
        </Button>
      </Group>
    </Stack>
  )
}
