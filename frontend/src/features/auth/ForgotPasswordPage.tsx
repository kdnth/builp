import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Alert,
  Anchor,
  Button,
  Container,
  Paper,
  Stack,
  Text,
  TextInput,
  Title,
} from '@mantine/core'
import { WarningCircleIcon } from '@phosphor-icons/react'
import { authClient } from '../../lib/auth'
import {
  classifyAuthError,
  passwordResetRequestErrorMessage,
} from '../../lib/authErrors'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setNotice(null)

    const normalizedEmail = email.trim()
    if (!normalizedEmail) {
      setError('Enter your account email.')
      return
    }

    setSubmitting(true)
    try {
      const result = await authClient.requestPasswordReset({
        email: normalizedEmail,
        redirectTo: `${window.location.origin}/reset-password`,
      })
      if (result.error) {
        const category = classifyAuthError(result.error)
        if (category === 'rate_limited' || category === 'service_unavailable') {
          setError(passwordResetRequestErrorMessage(result.error))
          return
        }

        // Keep behavior consistent for unknown/nonexistent emails to reduce
        // account enumeration opportunities.
        setNotice(
          'If an account exists for that email, we sent a password reset link.',
        )
        return
      }

      // Keep response wording consistent to avoid leaking account existence.
      setNotice(
        'If an account exists for that email, we sent a password reset link.',
      )
    } catch (caughtError) {
      setError(passwordResetRequestErrorMessage(caughtError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Container size="xs" py="xl">
      <Paper withBorder radius="md" p="lg">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Title order={2}>Forgot password</Title>
            <Text size="sm" c="dimmed">
              Enter your email and we will send a reset link.
            </Text>
            {notice && (
              <Alert color="green" radius="md">
                {notice}
              </Alert>
            )}
            {error && (
              <Alert
                color="red"
                icon={<WarningCircleIcon weight="fill" />}
                radius="md"
              >
                {error}
              </Alert>
            )}
            <TextInput
              label="Email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.currentTarget.value)}
              required
            />
            <Button type="submit" loading={submitting}>
              Send reset link
            </Button>
            <Text size="sm" c="dimmed">
              Remembered your password?{' '}
              <Anchor component={Link} to="/sign-in">
                Sign in
              </Anchor>
            </Text>
          </Stack>
        </form>
      </Paper>
    </Container>
  )
}
