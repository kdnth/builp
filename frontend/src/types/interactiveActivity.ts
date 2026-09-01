export type InteractiveActivity =
  | {
      type: 'matching'
      id: string
      description?: string
      pairs: { term: string; definition: string }[]
    }
  | {
      type: 'fillBlank'
      id: string
      description?: string
      text: string
      blanks: { position: number; accepted: string[] }[]
    }
  | {
      type: 'multipleChoice'
      id: string
      description?: string
      question: string
      options: string[]
      correctIndex: number
    }
