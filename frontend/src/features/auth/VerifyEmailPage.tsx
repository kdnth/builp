import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
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
import { authClient, refreshSession } from '../../lib/auth'
import { verificationErrorMessage } from '../../lib/authErrors'

export default function VerifyEmailPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const token = searchParams.get('token')
  const fromSignUp = searchParams.get('fromSignUp') === '1'
  const queryError = searchParams.get('error')?.toLowerCase()

  const [email, setEmail] = useState(() => searchParams.get('email') ?? '')
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(() => {
    if (queryError === 'invalid_token') {
      return 'That verification link is invalid or expired. Request a new one.'
    }
    return null
  })
  const [notice, setNotice] = useState<string | null>(() => {
    if (fromSignUp) {
      return 'Check your email for a verification code, then enter it below.'
    }
    return null
  })
  const [verifyingCode, setVerifyingCode] = useState(false)
  const [resending, setResending] = useState(false)
  const [verifyingLink, setVerifyingLink] = useState(false)

  useEffect(() => {
    const verificationToken = token
    if (!verificationToken) {
      return
    }

    let active = true

    async function verifyFromToken(verificationTokenValue: string) {
      setVerifyingLink(true)
      setError(null)
      setNotice('Finishing email verification...')
      try {
        const result = await authClient.verifyEmail({
          query: { token: verificationTokenValue },
        })
        if (!active) {
          return
        }
        if (result.error) {
          setNotice(null)
          setError(verificationErrorMessage(result.error))
          return
        }

        await refreshSession()
        const session = await authClient.getSession()
        if (!active) {
          return
        }
        if (session.data?.session) {
          navigate('/', { replace: true })
          return
        }
        navigate('/sign-in?verified=1', { replace: true })
      } catch (caughtError) {
        if (!active) {
          return
        }
        setNotice(null)
        setError(verificationErrorMessage(caughtError))
      } finally {
        if (active) {
          setVerifyingLink(false)
        }
      }
    }

    void verifyFromToken(verificationToken)
    return () => {
      active = false
    }
  }, [navigate, token])

  async function handleVerifyCode(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setNotice(null)

    const normalizedEmail = email.trim()
    const normalizedCode = code.trim()
    if (!normalizedEmail || !normalizedCode) {
      setError('Enter your email and verification code.')
      return
    }

    setVerifyingCode(true)
    try {
      const result = await authClient.emailOtp.verifyEmail({
        email: normalizedEmail,
        otp: normalizedCode,
      })
      if (result.error) {
        setError(verificationErrorMessage(result.error))
        return
      }

      await refreshSession()
      const session = await authClient.getSession()
      if (session.data?.session) {
        navigate('/', { replace: true })
        return
      }
      navigate('/sign-in?verified=1', { replace: true })
    } catch (caughtError) {
      setError(verificationErrorMessage(caughtError))
    } finally {
      setVerifyingCode(false)
    }
  }

  async function handleResend() {
    setError(null)
    setNotice(null)
    const normalizedEmail = email.trim()
    if (!normalizedEmail) {
      setError('Enter your email so we know where to send verification.')
      return
    }

    setResending(true)
    try {
      const origin = window.location.origin
      const callbackURL = `${origin}/verify-email?email=${encodeURIComponent(normalizedEmail)}`
      const linkResult = await authClient.sendVerificationEmail({
        email: normalizedEmail,
        callbackURL,
      })
      if (linkResult.error) {
        const otpResult = await authClient.emailOtp.sendVerificationOtp({
          email: normalizedEmail,
          type: 'email-verification',
        })
        if (otpResult.error) {
          setError(verificationErrorMessage(otpResult.error))
          return
        }
      }

      setNotice('Verification message sent. Check your inbox for a code or link.')
    } catch (caughtError) {
      setError(verificationErrorMessage(caughtError))
    } finally {
      setResending(false)
    }
  }

  return (
    <Container size="xs" py="xl">
      <Paper withBorder radius="md" p="lg">
        <form onSubmit={handleVerifyCode}>
          <Stack gap="md">
            <Title order={2}>Verify your email</Title>
            <Text size="sm" c="dimmed">
              Enter the verification code sent to your email. If your project is
              configured for verification links, you can also verify by clicking the
              link in your inbox.
            </Text>
            {verifyingLink && (
              <Alert color="blue" radius="md">
                Processing verification link...
              </Alert>
            )}
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
            <TextInput
              label="Verification code"
              value={code}
              onChange={(event) => setCode(event.currentTarget.value)}
              required
            />
            <Button type="submit" loading={verifyingCode} disabled={verifyingLink}>
              Verify email
            </Button>
            <Button
              type="button"
              variant="default"
              loading={resending}
              onClick={handleResend}
              disabled={verifyingLink}
            >
              Resend verification
            </Button>
            <Text size="sm" c="dimmed">
              Already verified?{' '}
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
