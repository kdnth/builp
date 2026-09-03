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
  TextInput,
  Title,
} from '@mantine/core'
import { WarningCircleIcon } from '@phosphor-icons/react'
import { authClient, refreshSession } from '../../lib/auth'
import { classifyAuthError, signInErrorMessage } from '../../lib/authErrors'

export default function SignInPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [needsVerification, setNeedsVerification] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const showVerifiedMessage = searchParams.get('verified') === '1'
  const showPasswordResetMessage = searchParams.get('passwordReset') === '1'
  const verifyEmailHref = email
    ? `/verify-email?email=${encodeURIComponent(email)}`
    : '/verify-email'

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setNeedsVerification(false)
    setSubmitting(true)
    try {
      const result = await authClient.signIn.email({ email, password })
      if (result.error) {
        setNeedsVerification(classifyAuthError(result.error) === 'email_unverified')
        setError(signInErrorMessage(result.error))
        return
      }
      await refreshSession()
      navigate('/')
    } catch (caughtError) {
      setError(signInErrorMessage(caughtError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Container size="xs" py="xl">
      <Paper withBorder radius="md" p="lg">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Title order={2}>Sign in</Title>
            {showVerifiedMessage && (
              <Alert color="green" radius="md">
                Your email is verified. You can sign in now.
              </Alert>
            )}
            {showPasswordResetMessage && (
              <Alert color="green" radius="md">
                Password updated. Sign in with your new password.
              </Alert>
            )}
            <TextInput
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.currentTarget.value)}
              required
            />
            <PasswordInput
              label="Password"
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
              required
            />
            {error && (
              <Alert
                color="red"
                icon={<WarningCircleIcon weight="fill" />}
                radius="md"
              >
                {error}
              </Alert>
            )}
            {needsVerification && (
              <Text size="sm" c="dimmed">
                Need to verify your email?{' '}
                <Anchor component={Link} to={verifyEmailHref}>
                  Enter your verification code
                </Anchor>
              </Text>
            )}
            <Text size="sm" c="dimmed">
              Forgot your password?{' '}
              <Anchor component={Link} to="/forgot-password">
                Reset it
              </Anchor>
            </Text>
            <Button type="submit" loading={submitting}>
              Sign in
            </Button>
            <Text size="sm" c="dimmed">
              No account yet?{' '}
              <Anchor component={Link} to="/sign-up">
                Sign up
              </Anchor>
            </Text>
          </Stack>
        </form>
      </Paper>
    </Container>
  )
}
