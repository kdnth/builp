import {
  javascript,
  javascriptLanguage,
  scopeCompletionSource,
} from '@codemirror/lang-javascript'
import { python } from '@codemirror/lang-python'
import { indentUnit } from '@codemirror/language'
import type { Extension } from '@codemirror/state'
import type { CodeLanguage } from '../../types/codeLanguage'
import { diagnosticsExtension } from './syntaxDiagnostics'

const javascriptGlobals = {
  Array,
  BigInt,
  Boolean,
  Date,
  Error,
  Infinity,
  JSON,
  Map,
  Math,
  NaN,
  Number,
  Object,
  Promise,
  RegExp,
  Set,
  String,
  Symbol,
  console,
  isFinite,
  isNaN,
  parseFloat,
  parseInt,
}

export function languageExtensions(language: CodeLanguage): Extension {
  switch (language) {
    case 'python':
      return [python(), indentUnit.of('    '), diagnosticsExtension(language)]
    case 'javascript':
      return [
        javascript(),
        javascriptLanguage.data.of({
          autocomplete: scopeCompletionSource(javascriptGlobals),
        }),
        indentUnit.of('  '),
        diagnosticsExtension(language),
      ]
  }
}
