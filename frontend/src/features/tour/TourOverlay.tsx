import { useEffect, useState, type CSSProperties } from 'react'
import { Button, Group, Paper, Portal, Text, Title } from '@mantine/core'
import { useTour } from './TourContext'

const SPOTLIGHT_PADDING = 8
const CARD_WIDTH = 340
const CARD_GAP = 12
const CARD_ESTIMATED_HEIGHT = 200

function useTargetRect(selector: string | null) {
  const [rect, setRect] = useState<DOMRect | null>(null)

  useEffect(() => {
    if (!selector) {
      setRect(null)
      return
    }

    function measure() {
      const el = document.querySelector(selector as string)
      setRect(el ? el.getBoundingClientRect() : null)
    }

    document
      .querySelector(selector)
      ?.scrollIntoView({ block: 'center', behavior: 'smooth' })

    measure()
    const timers = [50, 150, 300, 500].map((delay) =>
      window.setTimeout(measure, delay),
    )

    window.addEventListener('resize', measure)
    window.addEventListener('scroll', measure, true)

    return () => {
      timers.forEach(window.clearTimeout)
      window.removeEventListener('resize', measure)
      window.removeEventListener('scroll', measure, true)
    }
  }, [selector])

  return rect
}

export default function TourOverlay() {
  const { tour, next, back, end } = useTour()
  const step = tour?.steps[tour.stepIndex] ?? null
  const rect = useTargetRect(step?.target ?? null)

  if (!tour || !step) return null

  const isFirst = tour.stepIndex === 0
  const isLast = tour.stepIndex === tour.steps.length - 1

  const cardStyle: CSSProperties = rect
    ? (() => {
        const left = Math.min(
          Math.max(rect.left, 16),
          window.innerWidth - CARD_WIDTH - 16,
        )
        const belowTop = rect.bottom + SPOTLIGHT_PADDING + CARD_GAP
        const fitsBelow = belowTop + CARD_ESTIMATED_HEIGHT < window.innerHeight
        const top = fitsBelow
          ? belowTop
          : Math.max(
              rect.top - SPOTLIGHT_PADDING - CARD_GAP - CARD_ESTIMATED_HEIGHT,
              16,
            )
        return { position: 'fixed', left, top, width: CARD_WIDTH, zIndex: 1001 }
      })()
    : {
        position: 'fixed',
        left: '50%',
        top: '50%',
        transform: 'translate(-50%, -50%)',
        width: CARD_WIDTH,
        zIndex: 1001,
      }

  return (
    <Portal>
      <div
        onClick={end}
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 1000,
          background: rect ? 'transparent' : 'rgba(0, 0, 0, 0.5)',
        }}
      />
      {rect ? (
        <div
          style={{
            position: 'fixed',
            left: rect.left - SPOTLIGHT_PADDING,
            top: rect.top - SPOTLIGHT_PADDING,
            width: rect.width + SPOTLIGHT_PADDING * 2,
            height: rect.height + SPOTLIGHT_PADDING * 2,
            borderRadius: 8,
            boxShadow: '0 0 0 9999px rgba(0, 0, 0, 0.55)',
            outline: '2px solid var(--mantine-color-primary-6)',
            outlineOffset: 2,
            zIndex: 1000,
            pointerEvents: 'none',
            transition: 'left 150ms ease, top 150ms ease',
          }}
        />
      ) : null}
      <Paper shadow="lg" radius="md" p="md" withBorder style={cardStyle}>
        <Text size="xs" c="dimmed" mb={4}>
          Step {tour.stepIndex + 1} of {tour.steps.length}
        </Text>
        <Title order={5} mb={6}>
          {step.title}
        </Title>
        <Text size="sm" mb="md">
          {step.content}
        </Text>
        <Group justify="space-between">
          <Button variant="subtle" size="xs" onClick={end}>
            Skip tour
          </Button>
          <Group gap="xs">
            <Button
              variant="default"
              size="xs"
              onClick={back}
              disabled={isFirst}
            >
              Back
            </Button>
            <Button size="xs" onClick={next}>
              {isLast ? 'Done' : 'Next'}
            </Button>
          </Group>
        </Group>
      </Paper>
    </Portal>
  )
}
