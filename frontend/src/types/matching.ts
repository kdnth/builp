interface Pair {
  term: string
  definition: string
}

export interface Matching {
  type: 'matching'
  id: string
  description?: string
  pairs: Pair[]
}
