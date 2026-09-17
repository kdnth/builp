export interface Blank {
  position: number
  accepted: string[]
}

export interface FillBlank {
  type: 'fillBlank'
  id: string
  description?: string | null
  explanation?: string | null
  text: string
  blanks: Blank[]
}
