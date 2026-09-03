import { Link, Outlet } from 'react-router-dom'
import {
  ActionIcon,
  Anchor,
  AppShell,
  Group,
  Image,
  Title,
  useMantineColorScheme,
  useComputedColorScheme,
} from '@mantine/core'
import { MoonIcon, SunIcon } from '@phosphor-icons/react'
import AuthStatus from './AuthStatus'
import logo from '../../assets/logo.png'

function ColorSchemeToggle() {
  const { setColorScheme } = useMantineColorScheme()
  const computedColorScheme = useComputedColorScheme('light')

  function toggleColorScheme() {
    setColorScheme(computedColorScheme === 'dark' ? 'light' : 'dark')
  }

  return (
    <ActionIcon
      onClick={toggleColorScheme}
      variant="default"
      size="lg"
      aria-label="Toggle color scheme"
    >
      {computedColorScheme === 'dark' ? (
        <SunIcon size={18} />
      ) : (
        <MoonIcon size={18} />
      )}
    </ActionIcon>
  )
}

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
          <Group gap="sm">
            <AuthStatus />
            <ColorSchemeToggle />
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
    </AppShell>
  )
}
