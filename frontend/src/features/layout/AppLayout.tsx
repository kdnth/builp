import { Link, Outlet } from 'react-router-dom'
import { Anchor, AppShell, Group, Image, Title } from '@mantine/core'
import AuthStatus from './AuthStatus'
import logo from '../../assets/logo.png'

export default function AppLayout() {
  return (
    <AppShell header={{ height: 60 }} padding={0}>
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Anchor component={Link} to="/" underline="never" c="inherit">
            <Group gap="xs">
              <Image src={logo} w={48} h={48} fit="contain" />
              <Title order={2}>builp</Title>
            </Group>
          </Anchor>
          <AuthStatus />
        </Group>
      </AppShell.Header>
      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  )
}
