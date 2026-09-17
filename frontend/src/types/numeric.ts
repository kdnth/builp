export interface Numeric {
  type: 'numeric'
  id: string
  description?: string | null
  explanation?: string | null
  question: string
  answer: number
  tolerance: number
  unit?: string | null
}
