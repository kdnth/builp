import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  Alert,
  Anchor,
  Button,
  Container,
  Paper,
  PasswordInput,
  Stack,
  Text,
  Title,
} from '@mantine/core'
import { WarningCircleIcon } from '@phosphor-icons/react'
import { authClient, refreshSession } from '../../lib/auth'
import { passwordResetErrorMessage } from '../../lib/authErrors'

function isInvalidTokenError(queryError: string | null): boolean {
  if (!queryError) {
    return false
  }
  const normalized = queryError.toLowerCase()
  return normalized === 'invalid_token' || normalized === 'invalid-token'
}

export default function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const token = searchParams.get('token')
  const queryError = searchParams.get('error')
  const hasTokenIssue = isInvalidTokenError(queryError) || !token

  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(
    hasTokenIssue
      ? 'This reset link is invalid or expired. Request a new password reset email.'
      : null,
  )
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)

    if (!token || hasTokenIssue) {
      setError('This reset link is invalid or expired. Request a new one.')
      return
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setSubmitting(true)
    try {
      const result = await authClient.resetPassword({
        newPassword,
        token,
      })
      if (result.error) {
        setError(passwordResetErrorMessage(result.error))
        return
      }

      await refreshSession()
      const session = await authClient.getSession()
      if (session.data?.session) {
        navigate('/', { replace: true })
        return
      }
      navigate('/sign-in?passwordReset=1', { replace: true })
    } catch (caughtError) {
      setError(passwordResetErrorMessage(caughtError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Container size="xs" py="xl">
      <Paper withBorder radius="md" p="lg">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Title order={2}>Set a new password</Title>
            {error && (
              <Alert
                color="red"
                icon={<WarningCircleIcon weight="fill" />}
                radius="md"
              >
                {error}
              </Alert>
            )}
            {!token && (
              <Text size="sm" c="dimmed">
                Request a fresh reset link to continue.
              </Text>
            )}
            <PasswordInput
              label="New password"
              value={newPassword}
              onChange={(event) => setNewPassword(event.currentTarget.value)}
              minLength={8}
              required
              disabled={hasTokenIssue}
            />
            <PasswordInput
              label="Confirm new password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.currentTarget.value)}
              minLength={8}
              required
              disabled={hasTokenIssue}
            />
            <Button type="submit" loading={submitting} disabled={hasTokenIssue}>
              Reset password
            </Button>
            <Text size="sm" c="dimmed">
              Need a new link?{' '}
              <Anchor component={Link} to="/forgot-password">
                Request reset email
              </Anchor>
            </Text>
          </Stack>
        </form>
      </Paper>
    </Container>
  )
}
