export const failedMessages = [
  'Not quite! Try again',
  'Try that again',
  'Whoops. Not that one!',
]

export const passedMessages = [
  'Great job!',
  'Right on the money!',
  'You got it!',
  'WOAH. Super smarty alert!',
  "Nice, that's right!",
]

export function pickRandomMessage(messages: string[]): string {
  const randomIdx = Math.floor(Math.random() * messages.length)
  return messages[randomIdx]
}
