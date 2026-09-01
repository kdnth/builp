import type { InteractiveActivity } from './interactiveActivity'

export interface InteractivePractice {
  id: string
  title: string
  activities: InteractiveActivity[]
}
