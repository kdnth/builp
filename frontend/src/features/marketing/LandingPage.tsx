import { Link } from 'react-router-dom'
import {
  Button,
  Container,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import {
  ChartLineUpIcon,
  CodeIcon,
  ListChecksIcon,
} from '@phosphor-icons/react'

const features = [
  {
    icon: CodeIcon,
    title: 'Run real code',
    description:
      'Practice functions and components with live tests and a live preview.',
  },
  {
    icon: ListChecksIcon,
    title: 'Interactive practice',
    description:
      'Fill-in-the-blank, matching, and multiple choice, checked as you go.',
  },
  {
    icon: ChartLineUpIcon,
    title: 'Track your progress',
    description:
      'Lessons unlock in order, so you always know where you left off.',
  },
]

export default function LandingPage() {
  return (
    <Container size="md" py={80}>
      <Stack gap={60}>
        <Stack gap="md" align="center" ta="center">
          <Title order={1} size={42}>
            Take courses, your way
          </Title>
          <Text size="lg" c="dimmed" maw={520}>
            builp is a hands-on way to learn to new concepts. Build courses with
            written lessons, runnable code and interactive practice.
          </Text>
          <Group mt="md">
            <Button component={Link} to="/sign-up" size="md">
              Get started
            </Button>
            <Button component={Link} to="/sign-in" variant="default" size="md">
              Sign in
            </Button>
          </Group>
        </Stack>

        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="lg">
          {features.map((feature) => (
            <Paper key={feature.title} withBorder radius="md" p="lg">
              <Stack gap="xs">
                <feature.icon size={24} weight="fill" />
                <Text fw={600}>{feature.title}</Text>
                <Text size="sm" c="dimmed">
                  {feature.description}
                </Text>
              </Stack>
            </Paper>
          ))}
        </SimpleGrid>
      </Stack>
    </Container>
  )
}
