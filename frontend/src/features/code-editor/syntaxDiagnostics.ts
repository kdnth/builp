import { ensureSyntaxTree, syntaxTree } from '@codemirror/language'
import { forceLinting, linter, type Diagnostic } from '@codemirror/lint'
import {
  StateEffect,
  StateField,
  type EditorState,
  type Extension,
} from '@codemirror/state'
import type { EditorView } from '@codemirror/view'
import type { LineDiagnostic } from '../code-runner/types'
import type { CodeLanguage } from '../../types/codeLanguage'

const setRunDiagnostics = StateEffect.define<LineDiagnostic[]>()

export const runDiagnosticsField = StateField.define<LineDiagnostic[]>({
  create: () => [],
  update(value, tr) {
    for (const effect of tr.effects) {
      if (effect.is(setRunDiagnostics)) return effect.value
    }
    return tr.docChanged ? [] : value
  },
})

export function showRunDiagnostics(
  view: EditorView,
  diagnostics: LineDiagnostic[],
) {
  view.dispatch({ effects: setRunDiagnostics.of(diagnostics) })
  forceLinting(view)
}

function javascriptSyntaxError(code: string): string | null {
  try {
    new Function(code)
    return null
  } catch (err) {
    return err instanceof SyntaxError ? `SyntaxError: ${err.message}` : null
  }
}

function visibleRange(state: EditorState, from: number, to: number) {
  if (from !== to) return { from, to }
  let line = state.doc.lineAt(from)
  while (line.number > 1 && !line.text.trim()) {
    line = state.doc.line(line.number - 1)
  }
  const start = line.text.search(/\S/)
  if (start === -1) return { from, to }
  return {
    from: line.from + start,
    to: line.from + line.text.trimEnd().length,
  }
}

function firstParseError(state: EditorState, message: string): Diagnostic[] {
  const tree =
    ensureSyntaxTree(state, state.doc.length, 200) ?? syntaxTree(state)
  const found: Diagnostic[] = []
  tree.iterate({
    enter: (node) => {
      if (found.length > 0) return false
      if (!node.type.isError) return
      found.push({
        ...visibleRange(state, node.from, node.to),
        severity: 'error',
        message,
      })
      return false
    },
  })
  return found
}

function parserDiagnostics(
  state: EditorState,
  language: CodeLanguage,
): Diagnostic[] {
  if (language === 'python') return firstParseError(state, 'Syntax error')
  const message = javascriptSyntaxError(state.doc.toString())
  return message ? firstParseError(state, message) : []
}

function runDiagnostics(state: EditorState): Diagnostic[] {
  return state.field(runDiagnosticsField).flatMap(({ line, message }) => {
    if (line < 1 || line > state.doc.lines) return []
    const { from, to } = state.doc.line(line)
    return [{ from, to, severity: 'error' as const, message }]
  })
}

export function diagnosticsExtension(language: CodeLanguage): Extension {
  return linter(
    (view) => [
      ...parserDiagnostics(view.state, language),
      ...runDiagnostics(view.state),
    ],
    {
      delay: 500,
      needsRefresh: (update) =>
        update.transactions.some((tr) =>
          tr.effects.some((effect) => effect.is(setRunDiagnostics)),
        ),
    },
  )
}
