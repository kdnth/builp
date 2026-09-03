import { Link } from 'react-router-dom'
import { Button, Group, Text } from '@mantine/core'
import { SignOutIcon } from '@phosphor-icons/react'
import { authClient, refreshSession, useAuthSession } from '../../lib/auth'

export default function AuthStatus() {
  const session = useAuthSession()

  async function handleSignOut() {
    await authClient.signOut()
    await refreshSession()
  }

  if (session.isPending) {
    return null
  }

  if (session.data) {
    return (
      <Group gap="sm">
        <Text size="sm">{session.data.user.name}</Text>
        <Button
          variant="default"
          size="xs"
          leftSection={<SignOutIcon size={14} />}
          onClick={handleSignOut}
        >
          Sign out
        </Button>
      </Group>
    )
  }

  return (
    <Group gap="sm">
      <Button component={Link} to="/sign-in" variant="default" size="xs">
        Sign in
      </Button>
      <Button component={Link} to="/sign-up" size="xs">
        Sign up
      </Button>
    </Group>
  )
}
