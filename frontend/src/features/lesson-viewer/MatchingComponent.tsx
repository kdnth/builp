import { Button, Grid, Group, Paper, Stack, Text } from '@mantine/core'
import type { Matching } from '../../types/matching'
import { useEffect, useState } from 'react'
import { shuffle } from '../../helpers/shuffle'
import type { ActivityStatus } from '../../types/activityStatus'
import {
  failedMessages,
  passedMessages,
  pickRandomMessage,
} from '../../helpers/activityMessages'
import ActivityHeader from './ActivityHeader'
import ActivityAlert from './ActivityAlert'

interface MatchingComponentProps {
  activity: Matching
  onComplete: (activityId: string, isComplete: boolean) => void
}

interface Tile {
  id: string
  label: string
}

interface Match {
  termId: string | null
  definitionId: string | null
}
const emptyMatch: Match = {
  termId: null,
  definitionId: null,
}

function buildTiles(pairs: Matching['pairs'], key: 'term' | 'definition') {
  return shuffle(pairs.map((p) => ({ id: p.id, label: p[key] })))
}

export default function MatchingComponent({
  activity,
  onComplete,
}: MatchingComponentProps) {
  const [selection, setSelection] = useState<Match>(emptyMatch)
  const [incorrectSelection, setIncorrectSelection] = useState<Match>(emptyMatch)
  const [matchedPairIds, setMatchedPairIds] = useState<Set<string>>(new Set())
  const [status, setStatus] = useState<ActivityStatus>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [attempts, setAttempts] = useState(0)

  const [termTiles, setTermTiles] = useState<Tile[]>(() =>
    buildTiles(activity.pairs, 'term'),
  )
  const [definitionTiles, setDefinitionTiles] = useState<Tile[]>(() =>
    buildTiles(activity.pairs, 'definition'),
  )

  const maxAttempts = 3
  const revealed = status === 'revealed'
  const isComplete = matchedPairIds.size === activity.pairs.length

  useEffect(() => {
    onComplete(activity.id, isComplete)
  }, [isComplete, activity.id, onComplete])

  const handleTermTileClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    if (matchedPairIds.has(e.currentTarget.value)) return
    setIncorrectSelection(emptyMatch)
    setStatus(null)
    setMessage(null)

    const newSelection = {
      termId: e.currentTarget.value,
      definitionId: selection.definitionId,
    }

    setSelection(newSelection)
    checkMatch(newSelection)
  }

  const handleDefinitionTileClick = (
    e: React.MouseEvent<HTMLButtonElement>,
  ) => {
    if (matchedPairIds.has(e.currentTarget.value)) return
    setIncorrectSelection(emptyMatch)
    setStatus(null)
    setMessage(null)

    const newSelection = {
      termId: selection.termId,
      definitionId: e.currentTarget.value,
    }
    setSelection(newSelection)
    checkMatch(newSelection)
  }

  const handleIncorrectMatch = (selection: Match) => {
    setIncorrectSelection(selection)
    setSelection(emptyMatch)
    setStatus('incorrect')
    setMessage(pickRandomMessage(failedMessages))
    setAttempts((prev) => prev + 1)
  }

  const handleMatch = (selection: Match) => {
    if (selection.termId === null) return

    const next = new Set(matchedPairIds)
    next.add(selection.termId)
    setMatchedPairIds(next)
    setSelection(emptyMatch)

    if (next.size === activity.pairs.length) {
      setStatus('correct')
      setMessage(pickRandomMessage(passedMessages))
    }
  }

  const checkMatch = (selection: Match) => {
    if (selection.definitionId === null || selection.termId === null) {
      return
    } else if (selection.definitionId === selection.termId) {
      handleMatch(selection)
    } else {
      handleIncorrectMatch(selection)
    }
  }

  function handleShowAnswer() {
    setMatchedPairIds(new Set(activity.pairs.map((p) => p.id)))
    setSelection(emptyMatch)
    setIncorrectSelection(emptyMatch)
    setStatus('revealed')
    setMessage("Here's the answer.")
  }

  function handleRedo() {
    setSelection(emptyMatch)
    setIncorrectSelection(emptyMatch)
    setMatchedPairIds(new Set())
    setStatus(null)
    setMessage(null)
    setAttempts(0)
    setTermTiles(buildTiles(activity.pairs, 'term'))
    setDefinitionTiles(buildTiles(activity.pairs, 'definition'))
  }

  return (
    <Paper withBorder radius="md" p="lg">
      <Stack gap={'md'}>
        <ActivityHeader title="Match Terms" status={status} onRedo={handleRedo} />
        <Text>
          {activity.description != null
            ? activity.description
            : 'Match related terms'}
        </Text>

        <Grid>
          <Grid.Col span={4}>
            <Stack gap={'sm'}>
              {termTiles.map((t) => (
                <Button
                  key={t.id}
                  value={t.id}
                  onClick={handleTermTileClick}
                  variant={
                    matchedPairIds.has(t.id)
                      ? 'filled'
                      : t.id === selection.termId
                        ? 'filled'
                        : 'outline'
                  }
                  color={
                    matchedPairIds.has(t.id)
                      ? revealed
                        ? 'yellow'
                        : 'green'
                      : t.id === selection.termId
                        ? 'blue'
                        : t.id === incorrectSelection.termId
                          ? 'red'
                          : 'gray'
                  }
                >
                  {t.label}
                </Button>
              ))}
            </Stack>
          </Grid.Col>
          <Grid.Col span={4}>
            <Stack gap={'sm'}>
              {definitionTiles.map((t) => (
                <Button
                  key={t.id}
                  value={t.id}
                  onClick={handleDefinitionTileClick}
                  variant={
                    matchedPairIds.has(t.id)
                      ? 'filled'
                      : t.id === selection.definitionId
                        ? 'filled'
                        : 'outline'
                  }
                  color={
                    matchedPairIds.has(t.id)
                      ? revealed
                        ? 'yellow'
                        : 'green'
                      : t.id === selection.definitionId
                        ? 'blue'
                        : t.id === incorrectSelection.definitionId
                          ? 'red'
                          : 'gray'
                  }
                >
                  {t.label}
                </Button>
              ))}
            </Stack>
          </Grid.Col>
        </Grid>
        <ActivityAlert status={status} message={message} />
        {!isComplete && attempts >= maxAttempts && (
          <Group gap="xs">
            <Button variant="outline" color="yellow" onClick={handleShowAnswer}>
              Show Answer
            </Button>
          </Group>
        )}
      </Stack>
    </Paper>
  )
}
