import type { InteractiveActivity } from '../../types/interactiveActivity'
import CategorizeComponent from './CategorizeComponent'
import FillBlankComponent from './FillBlankComponent'
import MatchingComponent from './MatchingComponent'
import MultipleChoiceComponent from './MultipleChoiceComponent'
import NumericComponent from './NumericComponent'
import OrderingComponent from './OrderingComponent'

interface ActivityComponentRendererProps {
  activity: InteractiveActivity
  onComplete: (activityId: string, isComplete: boolean) => void
}

export default function ActivityComponentRenderer({
  activity,
  onComplete,
}: ActivityComponentRendererProps) {
  switch (activity.type) {
    case 'multipleChoice':
      return (
        <MultipleChoiceComponent activity={activity} onComplete={onComplete} />
      )
    case 'fillBlank':
      return <FillBlankComponent activity={activity} onComplete={onComplete} />
    case 'matching':
      return <MatchingComponent activity={activity} onComplete={onComplete} />
    case 'ordering':
      return <OrderingComponent activity={activity} onComplete={onComplete} />
    case 'categorize':
      return <CategorizeComponent activity={activity} onComplete={onComplete} />
    case 'numeric':
      return <NumericComponent activity={activity} onComplete={onComplete} />
  }
}
