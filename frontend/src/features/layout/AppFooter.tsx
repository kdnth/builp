import { Link } from 'react-router-dom'
import { Anchor, Container, Divider, Group, Stack, Text } from '@mantine/core'

export default function AppFooter() {
  return (
    <>
      <Divider mt="xl" />
      <Container size="lg" py="lg">
        <Stack gap="xs">
          <Group justify="space-between" gap="md">
            <Text size="sm" c="dimmed">
              builp
            </Text>
            <Group gap="lg" wrap="wrap">
              <Anchor component={Link} to="/contact" size="sm" c="dimmed">
                Contact
              </Anchor>
              <Anchor href="mailto:hello@kdnth.co" size="sm" c="dimmed">
                hello@kdnth.co
              </Anchor>
              <Anchor href="mailto:support@kdnth.co" size="sm" c="dimmed">
                support@kdnth.co
              </Anchor>
            </Group>
          </Group>
          <Text size="xs" c="dimmed">
            Found a problem in a course? Use the Report a problem link on the
            course page so the author hears about it.
          </Text>
        </Stack>
      </Container>
    </>
  )
}
