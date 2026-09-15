import { Button } from '@mantine/core'

interface MatchingTileProps {
  id: string
  label: string
  isMatched: boolean
  isSelected: boolean
  isIncorrect: boolean
  revealed: boolean
  onClick: (e: React.MouseEvent<HTMLButtonElement>) => void
}

const tileLabelStyle: React.CSSProperties = {
  minWidth: 0,
  overflow: 'auto',
  whiteSpace: 'wrap',
  textAlign: 'center',
}

export default function MatchingTile({
  id,
  label,
  isMatched,
  isSelected,
  isIncorrect,
  revealed,
  onClick,
}: MatchingTileProps) {
  return (
    <Button
      value={id}
      title={label}
      fullWidth
      h={44}
      justify="flex-start"
      styles={{ inner: { minWidth: 0 }, label: tileLabelStyle }}
      onClick={onClick}
      variant="light"
      color={
        isMatched
          ? revealed
            ? 'yellow'
            : 'green'
          : isSelected
            ? 'blue'
            : isIncorrect
              ? 'red'
              : 'gray'
      }
    >
      {label}
    </Button>
  )
}
