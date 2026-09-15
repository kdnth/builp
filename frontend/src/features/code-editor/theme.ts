import { HighlightStyle, syntaxHighlighting } from '@codemirror/language'
import type { Extension } from '@codemirror/state'
import { EditorView } from '@codemirror/view'
import { tags as t } from '@lezer/highlight'

type ColorScheme = 'light' | 'dark'

const shades: Record<ColorScheme, number> = { light: 8, dark: 3 }

function color(name: string, scheme: ColorScheme) {
  return `var(--mantine-color-${name}-${shades[scheme]})`
}

function highlightStyle(scheme: ColorScheme) {
  return HighlightStyle.define([
    { tag: t.keyword, color: color('grape', scheme) },
    {
      tag: [t.string, t.special(t.string), t.regexp],
      color: color('green', scheme),
    },
    { tag: [t.number, t.bool, t.null, t.atom], color: color('orange', scheme) },
    {
      tag: [
        t.function(t.variableName),
        t.function(t.definition(t.variableName)),
      ],
      color: color('blue', scheme),
    },
    { tag: t.function(t.propertyName), color: color('blue', scheme) },
    { tag: [t.className, t.typeName], color: color('teal', scheme) },
    { tag: t.propertyName, color: color('cyan', scheme) },
    { tag: [t.self, t.special(t.variableName)], color: color('pink', scheme) },
    {
      tag: t.comment,
      color: 'var(--mantine-color-dimmed)',
      fontStyle: 'italic',
    },
    { tag: t.invalid, color: color('red', scheme) },
  ])
}

function baseTheme(scheme: ColorScheme) {
  return EditorView.theme(
    {
      '&': {
        fontSize: 'var(--mantine-font-size-sm)',
        color: 'var(--mantine-color-text)',
        backgroundColor: 'var(--mantine-color-body)',
        border: '1px solid var(--mantine-color-default-border)',
        borderRadius: 'var(--mantine-radius-md)',
      },
      '&.cm-focused': {
        outline: 'none',
        borderColor: 'var(--mantine-primary-color-filled)',
      },
      '.cm-scroller': {
        fontFamily: 'var(--mantine-font-family-monospace)',
        lineHeight: '1.6',
      },
      '.cm-content, .cm-gutter': { minHeight: '6.4em' },
      '.cm-gutters': {
        color: 'var(--mantine-color-dimmed)',
        backgroundColor: 'var(--mantine-color-default-hover)',
        borderRight: '1px solid var(--mantine-color-default-border)',
        borderTopLeftRadius: 'var(--mantine-radius-md)',
        borderBottomLeftRadius: 'var(--mantine-radius-md)',
      },
      '.cm-activeLine, .cm-activeLineGutter': {
        backgroundColor:
          scheme === 'dark'
            ? 'rgba(255, 255, 255, 0.04)'
            : 'rgba(0, 0, 0, 0.03)',
      },
      '&:not(.cm-focused) .cm-activeLine, &:not(.cm-focused) .cm-activeLineGutter':
        {
          backgroundColor: 'transparent',
        },
    },
    { dark: scheme === 'dark' },
  )
}

export function editorTheme(scheme: ColorScheme): Extension {
  return [baseTheme(scheme), syntaxHighlighting(highlightStyle(scheme))]
}
