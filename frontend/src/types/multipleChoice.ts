export interface MultipleChoice {
  type: 'multipleChoice'
  id: string
  description?: string | null
  question: string
  options: string[]
  correctIndex: number
}
