interface Pair {
  id: string,
  term: string
  definition: string
}

export interface Matching {
  type: 'matching'
  id: string
  description?: string
  pairs: Pair[]
}
