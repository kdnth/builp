import type { CodeLanguage } from '../types/codeLanguage'

export interface ParsedFunctionSignature {
  name: string
  params: string[]
}

export function parseFunctionSignature(
  signature: string,
): ParsedFunctionSignature {
  const match = signature.match(/^([a-zA-Z_$][\w$]*)\s*\(([^)]*)\)/)
  if (!match) {
    return { name: signature.trim(), params: [] }
  }

  const [, name, paramsRaw] = match
  const params = paramsRaw
    .split(',')
    .map((p) => {
      const equalsIndex = p.indexOf('=')
      const head = equalsIndex === -1 ? p : p.slice(0, equalsIndex)
      const paramName = head.split(':')[0].trim()
      if (!paramName || equalsIndex === -1) return paramName
      return `${paramName}=${p.slice(equalsIndex + 1).trim()}`
    })
    .filter(Boolean)

  return { name, params }
}

export function buildStarterCode(
  signature: string,
  language: CodeLanguage,
): string {
  const { name, params } = parseFunctionSignature(signature)
  switch (language) {
    case 'python':
      return `def ${name}(${params.join(', ')}):\n    pass\n`
    case 'javascript':
      return `function ${name}(${params.join(', ')}) {\n  \n}\n`
  }
}
