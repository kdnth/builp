import { Link } from 'react-router-dom'
import {
  ActionIcon,
  Anchor,
  Group,
  Indicator,
  Menu,
  ScrollArea,
  Stack,
  Text,
} from '@mantine/core'
import { BellIcon } from '@phosphor-icons/react'
import { useNotifications } from './useNotifications'
import type { AppNotification } from '../../lib/api'

function relativeTime(iso: string): string {
  const then = new Date(iso).getTime()
  if (Number.isNaN(then)) return ''
  const minutes = Math.round((Date.now() - then) / 60000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.round(hours / 24)}d ago`
}

function NotificationItem({
  notification,
  onOpen,
}: {
  notification: AppNotification
  onOpen: (id: string) => void
}) {
  const unread = notification.read_at === null
  const content = (
    <Stack gap={2}>
      <Group gap="xs" wrap="nowrap" justify="space-between">
        <Text size="sm" fw={unread ? 600 : 400} lineClamp={1}>
          {notification.title}
        </Text>
        <Text size="xs" c="dimmed" style={{ whiteSpace: 'nowrap' }}>
          {relativeTime(notification.created_at)}
        </Text>
      </Group>
      <Text size="xs" c="dimmed" lineClamp={3}>
        {notification.body}
      </Text>
    </Stack>
  )

  if (notification.link) {
    return (
      <Menu.Item
        component={Link}
        to={notification.link}
        onClick={() => onOpen(notification.id)}
      >
        {content}
      </Menu.Item>
    )
  }
  return <Menu.Item onClick={() => onOpen(notification.id)}>{content}</Menu.Item>
}

export default function NotificationBell() {
  const { items, unreadCount, signedIn, refresh, markRead, markAllRead } =
    useNotifications()

  if (!signedIn) return null

  return (
    <Menu
      position="bottom-end"
      width={340}
      shadow="md"
      onOpen={() => void refresh()}
    >
      <Menu.Target>
        <Indicator
          disabled={unreadCount === 0}
          label={unreadCount > 9 ? '9+' : unreadCount}
          size={16}
          offset={4}
        >
          <ActionIcon
            variant="default"
            size="lg"
            aria-label={
              unreadCount > 0
                ? `Notifications, ${unreadCount} unread`
                : 'Notifications'
            }
          >
            <BellIcon size={18} />
          </ActionIcon>
        </Indicator>
      </Menu.Target>
      <Menu.Dropdown>
        <Group justify="space-between" px="sm" py={6} wrap="nowrap">
          <Text size="sm" fw={600}>
            Notifications
          </Text>
          {unreadCount > 0 && (
            <Anchor
              component="button"
              type="button"
              size="xs"
              onClick={() => void markAllRead()}
            >
              Mark all read
            </Anchor>
          )}
        </Group>
        <Menu.Divider />
        {items.length === 0 ? (
          <Text size="sm" c="dimmed" px="sm" py="md">
            Nothing yet. Reports on courses you wrote show up here.
          </Text>
        ) : (
          <ScrollArea.Autosize mah={360}>
            {items.map((notification) => (
              <NotificationItem
                key={notification.id}
                notification={notification}
                onOpen={(id) => void markRead(id)}
              />
            ))}
          </ScrollArea.Autosize>
        )}
      </Menu.Dropdown>
    </Menu>
  )
}
