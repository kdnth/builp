import { useCallback, useState } from 'react'
import { bundledCourses } from '../data/courses'
import { loadCustomCourses, saveCustomCourse } from '../helpers/customCourses'
import type { Course } from '../types/course'

export function useCourses() {
  const [customCourses, setCustomCourses] = useState<Course[]>(() =>
    loadCustomCourses(),
  )

  const addCourse = useCallback((course: Course) => {
    setCustomCourses(saveCustomCourse(course))
  }, [])

  return { courses: [...bundledCourses, ...customCourses], addCourse }
}
