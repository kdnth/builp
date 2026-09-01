import { type Unit } from './unit'

export interface Course {
  id: string
  title: string
  units: Unit[]
}
