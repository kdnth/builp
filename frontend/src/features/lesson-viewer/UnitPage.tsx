import { Center, Loader } from '@mantine/core'
import { Navigate, useParams } from 'react-router-dom'
import { useCourse } from '../../hooks/useCourse'
import { useCourseProgress } from '../../hooks/useCourseProgress'
import { isUnitUnlocked } from '../../helpers/progress'
import UnitComponent from './UnitComponent'

export default function UnitPage() {
  const { courseId, unitId } = useParams<{ courseId: string; unitId: string }>()
  const { course, loading, notFound } = useCourse(courseId)
  const { completedLessonIds, markLessonComplete } = useCourseProgress(courseId ?? '')

  if (notFound) {
    return <Navigate to="/" replace />
  }

  if (loading || !course) {
    return (
      <Center py={80}>
        <Loader />
      </Center>
    )
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
