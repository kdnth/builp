import { type Unit } from './unit'

export type CourseType = 'programming' | 'general'

export interface Course {
  id: string
  title: string
  courseType: CourseType
  units: Unit[]
  forkedFromId?: string | null
}
