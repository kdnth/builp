interface Pair {
  id: string
  term: string
  definition: string
}

export interface Matching {
  type: 'matching'
  id: string
  description?: string | null
  explanation?: string | null
  pairs: Pair[]
}
