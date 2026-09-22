export interface CategorizeItem {
  id: string
  text: string
  category: string
}

export interface Categorize {
  type: 'categorize'
  id: string
  description?: string | null
  explanation?: string | null
  categories: string[]
  items: CategorizeItem[]
}
