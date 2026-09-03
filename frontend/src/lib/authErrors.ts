import { isAuthApiError, isAuthError } from '@neondatabase/auth'

export type AuthErrorCategory =
  | 'invalid_credentials'
  | 'email_unverified'
  | 'rate_limited'
  | 'service_unavailable'
  | 'unknown'

const INVALID_CREDENTIAL_CODES = new Set([
  'invalid_credentials',
  'invalid_email_or_password',
  'invalid_password',
  'user_not_found',
])

const EMAIL_UNVERIFIED_CODES = new Set([
  'email_not_confirmed',
  'email_not_verified',
  'email_not_verified_error',
])

const RATE_LIMIT_CODES = new Set([
  'over_request_rate_limit',
  'over_email_send_rate_limit',
  'too_many_requests',
])

const WEAK_PASSWORD_CODES = new Set([
  'weak_password',
  'password_too_short',
  'password_too_long',
])

const INVALID_TOKEN_CODES = new Set([
  'bad_jwt',
  'invalid_token',
  'invalid_grant',
  'session_expired',
])

type ErrorRecord = Record<string, unknown>

function asRecord(value: unknown): ErrorRecord | null {
  if (!value || typeof value !== 'object') {
    return null
  }
  return value as ErrorRecord
}

function normalizeCode(code: unknown): string | null {
  if (typeof code !== 'string') {
    return null
  }
  const normalized = code.trim().toLowerCase()
  return normalized.length > 0 ? normalized : null
}

function readCode(error: unknown): string | null {
  const direct = normalizeCode(asRecord(error)?.code)
  if (direct) {
    return direct
  }
  return normalizeCode(asRecord(asRecord(error)?.error)?.code)
}

function readStatus(error: unknown): number | null {
  const directStatus = asRecord(error)?.status
  if (typeof directStatus === 'number') {
    return directStatus
  }
  const nestedStatus = asRecord(asRecord(error)?.error)?.status
  if (typeof nestedStatus === 'number') {
    return nestedStatus
  }
  return null
}

function readMessage(error: unknown): string {
  if (typeof error === 'string') {
    return error
  }
  if (error instanceof Error) {
    return error.message
  }
  const direct = asRecord(error)?.message
  if (typeof direct === 'string') {
    return direct
  }
  const nested = asRecord(asRecord(error)?.error)?.message
  if (typeof nested === 'string') {
    return nested
  }
  return ''
}

function messageIncludes(error: unknown, needles: string[]): boolean {
  const message = readMessage(error).toLowerCase()
  return needles.some((needle) => message.includes(needle))
}

export function classifyAuthError(error: unknown): AuthErrorCategory {
  const code = readCode(error)
  if (code && INVALID_CREDENTIAL_CODES.has(code)) {
    return 'invalid_credentials'
  }
  if (code && EMAIL_UNVERIFIED_CODES.has(code)) {
    return 'email_unverified'
  }
  if (code && RATE_LIMIT_CODES.has(code)) {
    return 'rate_limited'
  }

  const status = readStatus(error)
  if (status === 429) {
    return 'rate_limited'
  }

  if (
    status === 401 &&
    messageIncludes(error, ['invalid', 'incorrect', 'credential', 'password'])
  ) {
    return 'invalid_credentials'
  }

  if (
    (status === 403 || status === 422) &&
    messageIncludes(error, ['verify', 'verification', 'confirmed'])
  ) {
    return 'email_unverified'
  }

  if (status !== null && status >= 500) {
    return 'service_unavailable'
  }

  if (isAuthError(error) || isAuthApiError(error)) {
    const authStatus = readStatus(error)
    if (authStatus !== null && authStatus >= 500) {
      return 'service_unavailable'
    }
  }

  if (error instanceof TypeError) {
    return 'service_unavailable'
  }

  if (messageIncludes(error, ['network', 'fetch', 'timed out'])) {
    return 'service_unavailable'
  }

  return 'unknown'
}

export function signInErrorMessage(error: unknown): string {
  const category = classifyAuthError(error)
  if (category === 'invalid_credentials') {
    return 'Email or password is incorrect.'
  }
  if (category === 'email_unverified') {
    return 'Please verify your email before signing in.'
  }
  if (category === 'rate_limited') {
    return 'Too many sign-in attempts. Please wait and try again.'
  }
  if (category === 'service_unavailable') {
    return 'Sign-in is temporarily unavailable. Check your connection and try again.'
  }
  return 'Could not sign in right now. Please try again.'
}

export function signUpErrorMessage(error: unknown): string {
  const code = readCode(error)
  if (code && WEAK_PASSWORD_CODES.has(code)) {
    return 'Password does not meet security requirements.'
  }
  const category = classifyAuthError(error)
  if (category === 'rate_limited') {
    return 'Too many sign-up attempts. Please wait and try again.'
  }
  if (category === 'service_unavailable') {
    return 'Sign-up is temporarily unavailable. Check your connection and try again.'
  }
  return 'Could not create your account right now. Please try again.'
}

export function verificationErrorMessage(error: unknown): string {
  const code = readCode(error)
  if (
    (code && INVALID_TOKEN_CODES.has(code)) ||
    messageIncludes(error, ['otp', 'token', 'invalid', 'expired'])
  ) {
    return 'That verification code or link is invalid or expired. Request a new one.'
  }
  const category = classifyAuthError(error)
  if (category === 'rate_limited') {
    return 'Too many verification attempts. Please wait and try again.'
  }
  if (category === 'service_unavailable') {
    return 'Email verification is temporarily unavailable. Please try again.'
  }
  return 'Could not verify your email. Please try again.'
}

export function passwordResetRequestErrorMessage(error: unknown): string {
  const category = classifyAuthError(error)
  if (category === 'rate_limited') {
    return 'Too many reset requests. Please wait before trying again.'
  }
  if (category === 'service_unavailable') {
    return 'Password reset is temporarily unavailable. Check your connection and try again.'
  }
  return 'Could not start password reset right now. Please try again.'
}

export function passwordResetErrorMessage(error: unknown): string {
  const code = readCode(error)
  if (
    (code && INVALID_TOKEN_CODES.has(code)) ||
    messageIncludes(error, ['token', 'invalid', 'expired'])
  ) {
    return 'This reset link is invalid or expired. Request a new one.'
  }
  if (code && WEAK_PASSWORD_CODES.has(code)) {
    return 'Password does not meet security requirements.'
  }
  const category = classifyAuthError(error)
  if (category === 'rate_limited') {
    return 'Too many reset attempts. Please wait and try again.'
  }
  if (category === 'service_unavailable') {
    return 'Password reset is temporarily unavailable. Check your connection and try again.'
  }
  return 'Could not reset your password. Please try again.'
}
