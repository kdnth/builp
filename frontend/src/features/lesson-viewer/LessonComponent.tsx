import { useCallback, useEffect, useState } from 'react'
import type { Lesson } from '../../types/lesson'
import {
  Box,
  Button,
  Group,
  Paper,
  Stack,
  Stepper,
  Text,
  Title,
} from '@mantine/core'
import { useMediaQuery } from '@mantine/hooks'
import { ArrowRightIcon } from '@phosphor-icons/react'
import type { LessonView } from '../../types/lessonView'
import {
  isCodePractice,
  isInteractivePractice,
  isWrittenLesson,
} from '../../helpers/typeGuards'
import { lessonPages } from '../../helpers/lessonPages'
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
  const pages: LessonView[] = lessonPages(lesson)
  const pageCount = pages.length
  const [active, setActive] = useState(0)
  const [practiceCompletion, setPracticeCompletion] = useState<
    Record<string, boolean>
  >({})
  const nextStep = () =>
    setActive((current) => (current < pageCount ? current + 1 : current))
  const prevStep = () =>
    setActive((current) => (current > 0 ? current - 1 : current))

  const handlePracticeComplete = useCallback(
    (practiceId: string, allComplete: boolean) => {
      setPracticeCompletion((prev) =>
        prev[practiceId] === allComplete
          ? prev
          : { ...prev, [practiceId]: allComplete },
      )
    },
    [],
  )

  useEffect(() => {
    if (active === pageCount) {
      onComplete?.()
    }
  }, [active, pageCount, onComplete])

  const compact = useMediaQuery('(max-width: 48em)') ?? false
  const currentPage = pages[active]
  const currentPageReady =
    currentPage === undefined ||
    !isInteractivePractice(currentPage) ||
    practiceCompletion[currentPage.id] === true

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
      {compact && (
        <Text size="sm" c="dimmed">
          {active < pageCount
            ? `Step ${active + 1} of ${pageCount}: ${pages[active].title}`
            : 'Lesson complete'}
        </Text>
      )}
      <Stepper
        active={active}
        onStepClick={setActive}
        // Step labels stack into a tall wall of text on a phone.
        styles={compact ? { steps: { display: 'none' } } : undefined}
      >
        {pages.map((page) => (
          <Stepper.Step
            key={page.id}
            label={page.title}
            description={getViewTypeString(page)}
          >
            <Box key={page.id} mt="md">
              <LessonViewRenderer
                view={page}
                onInteractivePracticeComplete={handlePracticeComplete}
              />
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
        <Button
          onClick={nextStep}
          disabled={active === pageCount || !currentPageReady}
        >
          Next
        </Button>
      </Group>
    </Stack>
  )
}
