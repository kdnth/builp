export interface MultipleChoice {
  type: 'multipleChoice'
  id: string
  description?: string | null
  explanation?: string | null
  passage?: string | null
  question: string
  options: string[]
  optionExplanations?: string[] | null
  correctIndex: number
}
