export interface ParsedFunctionSignature {
  name: string
  params: string[]
}

export function parseFunctionSignature(signature: string): ParsedFunctionSignature {
  const match = signature.match(/^([a-zA-Z_$][\w$]*)\s*\(([^)]*)\)/)
  if (!match) {
    return { name: signature.trim(), params: [] }
  }

  const [, name, paramsRaw] = match
  const params = paramsRaw
    .split(',')
    .map((p) => p.split(':')[0].trim())
    .filter(Boolean)

  return { name, params }
}

export function buildStarterCode(signature: string): string {
  const { name, params } = parseFunctionSignature(signature)
  return `function ${name}(${params.join(', ')}) {\n  \n}\n`
}
