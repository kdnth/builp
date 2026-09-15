import { Link, Outlet, useLocation } from 'react-router-dom'
import {
  ActionIcon,
  Anchor,
  AppShell,
  Box,
  Burger,
  Group,
  Image,
  NavLink,
  Title,
  useMantineColorScheme,
  useComputedColorScheme,
  Text,
} from '@mantine/core'
import { useDisclosure } from '@mantine/hooks'
import { Notifications } from '@mantine/notifications'
import {
  BookBookmarkIcon,
  CompassIcon,
  MoonIcon,
  SunIcon,
} from '@phosphor-icons/react'
import AuthStatus from './AuthStatus'
import GenerationJobIndicator from '../generation/GenerationJobIndicator'
import GenerationJobsWatcher from '../generation/GenerationJobsWatcher'
import logo from '../../assets/logo.png'

const navItems = [
  { to: '/explore', label: 'Explore', Icon: CompassIcon },
  { to: '/', label: 'My Courses', Icon: BookBookmarkIcon },
]

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
  const [opened, { toggle, close }] = useDisclosure(false)
  const { pathname } = useLocation()

  return (
    <AppShell
      header={{ height: 60 }}
      navbar={{
        width: 300,
        breakpoint: 'sm',
        collapsed: { mobile: !opened, desktop: true },
      }}
      padding={0}
    >
      <AppShell.Header>
        <Group h="100%" px="md" justify="space-between" wrap="nowrap">
          <Group gap={'lg'} wrap="nowrap">
            <Burger
              opened={opened}
              onClick={toggle}
              hiddenFrom="sm"
              size="sm"
              aria-label="Toggle navigation"
            />
            <Anchor
              component={Link}
              to="/"
              underline="never"
              c="inherit"
              onClick={close}
            >
              <Group gap="xs" wrap="nowrap">
                <Image src={logo} w={48} h={48} fit="contain" />
                <Title order={2}>builp</Title>
              </Group>
            </Anchor>
            <Group gap={'md'} visibleFrom="sm">
              {navItems.map(({ to, label, Icon }) => (
                <Anchor
                  key={to}
                  component={Link}
                  to={to}
                  underline="never"
                  c="dimmed"
                >
                  <Group gap={'xs'}>
                    <Icon size={16} />
                    <Text>{label}</Text>
                  </Group>
                </Anchor>
              ))}
            </Group>
          </Group>
          <Group gap="sm" wrap="nowrap">
            <GenerationJobIndicator />
            <Box visibleFrom="sm">
              <AuthStatus />
            </Box>
            <ColorSchemeToggle />
          </Group>
        </Group>
      </AppShell.Header>
      <AppShell.Navbar p="md">
        {navItems.map(({ to, label, Icon }) => (
          <NavLink
            key={to}
            component={Link}
            to={to}
            label={label}
            leftSection={<Icon size={16} />}
            active={pathname === to}
            onClick={close}
          />
        ))}
        <Box mt="md" onClick={close}>
          <AuthStatus />
        </Box>
      </AppShell.Navbar>
      <AppShell.Main>
        <Outlet />
      </AppShell.Main>
      <GenerationJobsWatcher />
      <Notifications position="bottom-right" />
    </AppShell>
  )
}
