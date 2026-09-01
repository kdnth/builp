export interface MultipleChoice {
  type: 'multipleChoice'
  id: string
  description?: string
  question: string
  options: string[]
  correctIndex: number
}
