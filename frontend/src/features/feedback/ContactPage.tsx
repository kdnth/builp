import { useEffect, useState } from 'react'
import {
  Alert,
  Anchor,
  Button,
  Container,
  Group,
  Paper,
  Stack,
  Text,
  TextInput,
  Textarea,
  Title,
} from '@mantine/core'
import { CheckCircleIcon, WarningCircleIcon } from '@phosphor-icons/react'
import { submitContactMessage } from '../../lib/api'
import { useAuthSession } from '../../lib/auth'

export default function ContactPage() {
  const session = useAuthSession()
  const signedInUser = session.data?.user
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [subject, setSubject] = useState('')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Prefill from the session once it resolves, without overwriting
    // anything already typed.
    if (!signedInUser) return
    setName((current) => current || signedInUser.name)
    setEmail((current) => current || signedInUser.email)
  }, [signedInUser])

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await submitContactMessage({
        name: name.trim(),
        email: email.trim(),
        subject: subject.trim(),
        message: message.trim(),
      })
      setSent(true)
      setSubject('')
      setMessage('')
    } catch (caughtError) {
      setError(
        caughtError instanceof Error
          ? caughtError.message
          : 'Could not send your message.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Container size="sm" py="xl">
      <Stack gap="lg">
        <Stack gap="xs">
          <Title order={2}>Contact</Title>
          <Text c="dimmed">
            Questions, feedback, or trouble with your account. For a problem
            inside a specific course, use Report a problem on that course page
            instead, so its author hears about it too.
          </Text>
        </Stack>

        {sent && (
          <Alert
            color="green"
            icon={<CheckCircleIcon weight="fill" size={20} />}
            title="Message sent"
          >
            Thanks. We reply to the address you gave.
          </Alert>
        )}

        {error && (
          <Alert
            color="red"
            icon={<WarningCircleIcon weight="fill" size={20} />}
            title="Could not send"
          >
            {error}
          </Alert>
        )}

        <Paper withBorder radius="md" p="lg">
          <form onSubmit={handleSubmit}>
            <Stack gap="md">
              <TextInput
                label="Your name"
                value={name}
                onChange={(e) => setName(e.currentTarget.value)}
                maxLength={120}
                required
              />
              <TextInput
                label="Email"
                description="Where we reply."
                type="email"
                value={email}
                onChange={(e) => setEmail(e.currentTarget.value)}
                required
              />
              <TextInput
                label="Subject"
                value={subject}
                onChange={(e) => setSubject(e.currentTarget.value)}
                maxLength={200}
                required
              />
              <Textarea
                label="Message"
                value={message}
                onChange={(e) => setMessage(e.currentTarget.value)}
                minRows={6}
                maxLength={5000}
                autosize
                required
              />
              <Group justify="space-between">
                <Text size="sm" c="dimmed">
                  Or email{' '}
                  <Anchor href="mailto:hello@kdnth.co">hello@kdnth.co</Anchor>
                </Text>
                <Button type="submit" loading={submitting}>
                  Send message
                </Button>
              </Group>
            </Stack>
          </form>
        </Paper>
      </Stack>
    </Container>
  )
}
