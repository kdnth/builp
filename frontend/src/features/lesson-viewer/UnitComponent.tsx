import { useState } from 'react'
import type { Unit } from '../../types/unit'
import { Box, Container, Paper, Stack, Stepper, Title } from '@mantine/core'
import LessonComponent from './LessonComponent'

interface UnitComponentProps {
  unit: Unit
}
export default function UnitComponent({ unit }: UnitComponentProps) {
  const [active, setActive] = useState(0)

  return (
    <Container size="lg" py="xl">
      <Stack gap="lg">
        <Title order={1}>{unit.title}</Title>
        <Paper withBorder radius="md" p="lg" shadow="sm">
          <Stepper active={active} onStepClick={setActive}>
            {unit.lessons.map((lesson) => (
              <Stepper.Step key={lesson.id} label={lesson.title}>
                <Box mt="md">
                  <LessonComponent lesson={lesson} />
                </Box>
              </Stepper.Step>
            ))}
          </Stepper>
        </Paper>
      </Stack>
    </Container>
  )
}
