export interface Ordering {
  type: 'ordering'
  id: string
  description?: string | null
  explanation?: string | null
  basis: string
  items: string[]
}
