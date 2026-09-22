import { Alert, Typography } from '@mantine/core'
import {
  InfoIcon,
  LightbulbIcon,
  WarningIcon,
  BookOpenIcon,
} from '@phosphor-icons/react'
import type { ComponentProps, ReactNode } from 'react'
import { Children, isValidElement, useEffect, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'

type RehypePlugins = ComponentProps<typeof Markdown>['rehypePlugins']

// KaTeX and its fonts are large, so a lesson without math never loads them.
let katexPlugins: RehypePlugins | null = null

function useMathPlugins(markdown: string): RehypePlugins {
  const needsMath = markdown.includes('$$')
  const [plugins, setPlugins] = useState<RehypePlugins>(katexPlugins ?? [])

  useEffect(() => {
    if (!needsMath || katexPlugins) return
    let cancelled = false
    void Promise.all([
      import('rehype-katex'),
      import('katex/dist/katex.min.css'),
    ]).then(([module]) => {
      katexPlugins = [module.default]
      if (!cancelled) setPlugins(katexPlugins)
    })
    return () => {
      cancelled = true
    }
  }, [needsMath])

  return needsMath ? plugins : []
}

const mathOptions = { singleDollarTextMath: false }

const CALLOUTS = {
  NOTE: { color: 'blue', label: 'Note', Icon: InfoIcon },
  TIP: { color: 'teal', label: 'Tip', Icon: LightbulbIcon },
  WARNING: { color: 'yellow', label: 'Watch out', Icon: WarningIcon },
  IMPORTANT: { color: 'grape', label: 'Important', Icon: BookOpenIcon },
} as const

function firstText(node: ReactNode): string {
  if (typeof node === 'string') return node
  if (Array.isArray(node)) {
    for (const child of node) {
      const text = firstText(child)
      if (text.trim()) return text
    }
    return ''
  }
  if (isValidElement(node)) {
    return firstText((node.props as { children?: ReactNode }).children)
  }
  return ''
}

/** GitHub alert syntax: a blockquote whose first line is `[!TIP]`. */
function Blockquote({ children }: { children?: ReactNode }) {
  // react-markdown puts newline strings between the elements it renders.
  const parts = Children.toArray(children).filter(
    (child) => typeof child !== 'string' || child.trim(),
  )
  const match = firstText(parts[0]).match(/^\[!(NOTE|TIP|WARNING|IMPORTANT)\]/)
  if (!match) return <blockquote>{children}</blockquote>

  const { color, label, Icon } = CALLOUTS[match[1] as keyof typeof CALLOUTS]
  const body = parts.map((child, index) =>
    index === 0 ? (
      <p key="lead">{firstText(child).replace(/^\[![A-Z]+\]\s*/, '')}</p>
    ) : (
      child
    ),
  )

  return (
    <Alert
      color={color}
      radius="md"
      title={label}
      icon={<Icon weight="fill" />}
    >
      {body}
    </Alert>
  )
}

interface LessonMarkdownProps {
  children: string
  inline?: boolean
}

export default function LessonMarkdown({
  children,
  inline = false,
}: LessonMarkdownProps) {
  const rehypePlugins = useMathPlugins(children)
  const markdown = (
    <Markdown
      remarkPlugins={[remarkGfm, [remarkMath, mathOptions]]}
      rehypePlugins={rehypePlugins}
      components={inline ? undefined : { blockquote: Blockquote }}
    >
      {children}
    </Markdown>
  )

  if (inline) {
    return <span className="lesson-markdown-inline">{markdown}</span>
  }
  return <Typography>{markdown}</Typography>
}
