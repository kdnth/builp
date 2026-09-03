import { createInternalNeonAuth } from '@neondatabase/auth'
import { BetterAuthReactAdapter } from '@neondatabase/auth/react/adapters'
import { useSyncExternalStore } from 'react'

const authUrl = import.meta.env.VITE_NEON_AUTH_URL as string | undefined

if (!authUrl) {
  console.warn(
    'VITE_NEON_AUTH_URL is not set. Sign in and sign up will not work until it is.',
  )
}

const { adapter: authClient, getJWTToken } = createInternalNeonAuth(
  authUrl ?? '',
  { adapter: BetterAuthReactAdapter() },
)

export { authClient, getJWTToken }

export interface AuthUser {
  id: string
  name: string
  email: string
}

interface SessionState {
  isPending: boolean
  data: { user: AuthUser } | null
}

// The SDK's own reactive session atom doesn't hold up across Vite's dev
// pre-bundling (throws "store.get is not a function"), so this is a small,
// dependency-free shared store instead, backed by the stable getSession()
// call. refreshSession() is called after sign-in/sign-up/sign-out so every
// subscriber (header, home route, ...) picks up the change immediately.
let sessionState: SessionState = { isPending: true, data: null }
const listeners = new Set<() => void>()

function setSessionState(next: SessionState) {
  sessionState = next
  listeners.forEach((listener) => listener())
}

export async function refreshSession(): Promise<void> {
  try {
    const result = await authClient.getSession()
    setSessionState({ isPending: false, data: result.data })
  } catch {
    setSessionState({ isPending: false, data: null })
  }
}

export function useAuthSession(): SessionState {
  return useSyncExternalStore(
    (onStoreChange) => {
      listeners.add(onStoreChange)
      return () => listeners.delete(onStoreChange)
    },
    () => sessionState,
  )
}

if (authUrl) {
  void refreshSession()
} else {
  setSessionState({ isPending: false, data: null })
}
