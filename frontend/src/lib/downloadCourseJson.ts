import type { CourseDetail } from './api'

function slugify(text: string): string {
  return text
    .toString()
    .toLowerCase()
    .trim()
    .replace(/\s+/g, '-')
    .replace(/[^\w-]+/g, '')
    .replace(/--+/g, '-')
}

// Strips tags/owner_user_id - DB-side metadata, not part of the course JSON
// contract - so the downloaded file is exactly what UploadCoursePage accepts.
export function downloadCourseJson(course: CourseDetail): void {
  const slug = slugify(course.title)
  const fileName = `${slug || 'download'}.json`
  const { owner_user_id: _owner_user_id, tags: _tags, ...cleanedCourse } = course
  const courseJsonString = JSON.stringify(cleanedCourse, null, 2)
  const blob = new Blob([courseJsonString], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')

  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)

  URL.revokeObjectURL(url)
}
