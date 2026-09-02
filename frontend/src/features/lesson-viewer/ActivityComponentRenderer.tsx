import type { InteractiveActivity } from '../../types/interactiveActivity'
import FillBlankComponent from './FillBlankComponent'
import MatchingComponent from './MatchingComponent'
import MultipleChoiceComponent from './MultipleChoiceComponent'

interface ActivityComponentRendererProps {
  activity: InteractiveActivity
  onComplete: (activityId: string, isComplete: boolean) => void
}
export default function ActivityComponentRenderer({
  activity,
  onComplete,
}: ActivityComponentRendererProps) {
  if (activity.type == 'multipleChoice') {
    return <MultipleChoiceComponent activity={activity} onComplete={onComplete} />
  } else if (activity.type == 'fillBlank') {
    return <FillBlankComponent activity={activity} onComplete={onComplete} />
  } else if (activity.type == 'matching') {
    return <MatchingComponent activity={activity} onComplete={onComplete} />
  }
}
