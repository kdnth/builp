import { javascript } from '@codemirror/lang-javascript'
import { python } from '@codemirror/lang-python'
import { indentUnit } from '@codemirror/language'
import type { Extension } from '@codemirror/state'
import type { CodeLanguage } from '../../types/codeLanguage'

export function languageExtensions(language: CodeLanguage): Extension {
  switch (language) {
    case 'python':
      return [python(), indentUnit.of('    ')]
    case 'javascript':
      return [javascript(), indentUnit.of('  ')]
  }
}
