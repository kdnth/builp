import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
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
import { signUpErrorMessage } from '../../lib/authErrors'

export default function SignUpPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const callbackURL = `${window.location.origin}/verify-email?email=${encodeURIComponent(email)}`
      const result = await authClient.signUp.email({
        email,
        password,
        name,
        callbackURL,
      })
      if (result.error) {
        setError(signUpErrorMessage(result.error))
        return
      }
      if (!result.data?.token || !result.data.user.emailVerified) {
        navigate(`/verify-email?email=${encodeURIComponent(email)}&fromSignUp=1`)
        return
      }
      await refreshSession()
      navigate('/')
    } catch (caughtError) {
      setError(signUpErrorMessage(caughtError))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Container size="xs" py="xl">
      <Paper withBorder radius="md" p="lg">
        <form onSubmit={handleSubmit}>
          <Stack gap="md">
            <Title order={2}>Sign up</Title>
            <TextInput
              label="Name"
              value={name}
              onChange={(e) => setName(e.currentTarget.value)}
              required
            />
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
              minLength={8}
              required
            />
            {error && (
              <Alert color="red" icon={<WarningCircleIcon weight="fill" />} radius="md">
                {error}
              </Alert>
            )}
            <Button type="submit" loading={submitting}>
              Sign up
            </Button>
            <Text size="sm" c="dimmed">
              Already have an account? <Anchor component={Link} to="/sign-in">Sign in</Anchor>
            </Text>
          </Stack>
        </form>
      </Paper>
    </Container>
  )
}
