export interface Blank {
  position: number
  accepted: string[]
}

export interface FillBlank {
  type: 'fillBlank'
  id: string
  description?: string
  text: string
  blanks: Blank[]
}
