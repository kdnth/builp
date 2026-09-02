import type { CodePractice } from '../../types/codePractice'
import FunctionPracticeView from './FunctionPracticeView'
import ComponentPracticeView from './ComponentPracticeView'

interface CodePracticeViewProps {
  view: CodePractice
}

export default function CodePracticeView({ view }: CodePracticeViewProps) {
  if (view.type === 'function') {
    return <FunctionPracticeView view={view} />
  }
  return <ComponentPracticeView view={view} />
}
