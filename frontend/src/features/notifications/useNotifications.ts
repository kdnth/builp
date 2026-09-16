import { useCallback, useEffect, useState } from 'react'
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type AppNotification,
} from '../../lib/api'
import { useAuthSession } from '../../lib/auth'

const POLL_INTERVAL_MS = 60000

export function useNotifications() {
  const session = useAuthSession()
  const signedIn = !session.isPending && session.data !== null
  const [items, setItems] = useState<AppNotification[]>([])
  const [unreadCount, setUnreadCount] = useState(0)

  const refresh = useCallback(async () => {
    if (!signedIn) return
    try {
      const data = await listNotifications()
      setItems(data.items)
      setUnreadCount(data.unread_count)
    } catch {
      // The bell is ambient. A failed poll leaves the last known state up
      // rather than pushing an error at someone mid-lesson.
    }
  }, [signedIn])

  useEffect(() => {
    if (!signedIn) {
      setItems([])
      setUnreadCount(0)
      return
    }
    void refresh()
    const intervalId = setInterval(() => void refresh(), POLL_INTERVAL_MS)
    return () => clearInterval(intervalId)
  }, [signedIn, refresh])

  const markRead = useCallback(async (notificationId: string) => {
    const readAt = new Date().toISOString()
    let wasUnread = false
    setItems((current) =>
      current.map((item) => {
        if (item.id !== notificationId || item.read_at) return item
        wasUnread = true
        return { ...item, read_at: readAt }
      }),
    )
    if (wasUnread) {
      setUnreadCount((count) => Math.max(0, count - 1))
    }
    try {
      await markNotificationRead(notificationId)
    } catch {
      void refresh()
    }
  }, [refresh])

  const markAllRead = useCallback(async () => {
    const readAt = new Date().toISOString()
    setItems((current) =>
      current.map((item) => (item.read_at ? item : { ...item, read_at: readAt })),
    )
    setUnreadCount(0)
    try {
      await markAllNotificationsRead()
    } catch {
      void refresh()
    }
  }, [refresh])

  return { items, unreadCount, signedIn, refresh, markRead, markAllRead }
}
