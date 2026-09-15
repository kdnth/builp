import { useComputedColorScheme } from '@mantine/core'
import { indentWithTab } from '@codemirror/commands'
import { Compartment, EditorState } from '@codemirror/state'
import { EditorView, keymap } from '@codemirror/view'
import { basicSetup } from 'codemirror'
import { useEffect, useRef } from 'react'
import type { CodeLanguage } from '../../types/codeLanguage'
import { languageExtensions } from './languages'
import { editorTheme } from './theme'

// Compartments are keys, not state, so all editors can share them.
const languageCompartment = new Compartment()
const themeCompartment = new Compartment()
const readOnlyCompartment = new Compartment()

function readOnlyExtensions(readOnly: boolean) {
  return [EditorState.readOnly.of(readOnly), EditorView.editable.of(!readOnly)]
}

interface CodeEditorProps {
  value: string
  onChange: (value: string) => void
  language: CodeLanguage
  readOnly?: boolean
}

export default function CodeEditor({
  value,
  onChange,
  language,
  readOnly = false,
}: CodeEditorProps) {
  const colorScheme = useComputedColorScheme('light')
  const containerRef = useRef<HTMLDivElement>(null)
  const viewRef = useRef<EditorView | null>(null)
  const onChangeRef = useRef(onChange)

  const initialRef = useRef({ value, language, readOnly, colorScheme })

  useEffect(() => {
    onChangeRef.current = onChange
  }, [onChange])

  useEffect(() => {
    const initial = initialRef.current
    const view = new EditorView({
      parent: containerRef.current!,
      state: EditorState.create({
        doc: initial.value,
        extensions: [
          basicSetup,
          keymap.of([indentWithTab]),
          languageCompartment.of(languageExtensions(initial.language)),
          themeCompartment.of(editorTheme(initial.colorScheme)),
          readOnlyCompartment.of(readOnlyExtensions(initial.readOnly)),
          EditorView.updateListener.of((update) => {
            if (update.docChanged) {
              onChangeRef.current(update.state.doc.toString())
            }
          }),
        ],
      }),
    })
    viewRef.current = view
    return () => {
      view.destroy()
      viewRef.current = null
    }
  }, [])

  useEffect(() => {
    viewRef.current?.dispatch({
      effects: languageCompartment.reconfigure(languageExtensions(language)),
    })
  }, [language])

  useEffect(() => {
    viewRef.current?.dispatch({
      effects: themeCompartment.reconfigure(editorTheme(colorScheme)),
    })
  }, [colorScheme])

  useEffect(() => {
    viewRef.current?.dispatch({
      effects: readOnlyCompartment.reconfigure(readOnlyExtensions(readOnly)),
    })
  }, [readOnly])

  useEffect(() => {
    const view = viewRef.current
    if (!view) return
    const current = view.state.doc.toString()
    if (current !== value) {
      view.dispatch({ changes: { from: 0, to: current.length, insert: value } })
    }
  }, [value])

  return <div ref={containerRef} />
}
