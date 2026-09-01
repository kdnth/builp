import { type Lesson } from './lesson'

export interface Unit {
  id: string
  title: string
  lessons: Lesson[]
}
