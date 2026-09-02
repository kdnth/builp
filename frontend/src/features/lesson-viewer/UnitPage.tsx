import { Navigate, useParams } from 'react-router-dom'
import { getCourse } from '../../data/courses'
import { useCourseProgress } from '../../hooks/useCourseProgress'
import { isUnitUnlocked } from '../../helpers/progress'
import UnitComponent from './UnitComponent'

export default function UnitPage() {
  const { courseId, unitId } = useParams<{ courseId: string; unitId: string }>()
  const course = courseId ? getCourse(courseId) : undefined
  const { completedLessonIds, markLessonComplete } = useCourseProgress(
    courseId ?? '',
  )

  if (!course) {
    return <Navigate to="/" replace />
  }

  const unitIndex = course.units.findIndex((u) => u.id === unitId)
  if (unitIndex === -1) {
    return <Navigate to={`/courses/${course.id}`} replace />
  }

  if (!isUnitUnlocked(completedLessonIds, course, unitIndex)) {
    return <Navigate to={`/courses/${course.id}`} replace />
  }

  return (
    <UnitComponent
      key={course.units[unitIndex].id}
      course={course}
      unitIndex={unitIndex}
      completedLessonIds={completedLessonIds}
      markLessonComplete={markLessonComplete}
    />
  )
}
