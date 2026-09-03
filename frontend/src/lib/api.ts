import type { Course } from '../types/course'
import { getJWTToken } from './auth'

const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? ''

async function authorizedFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const token = await getJWTToken()
  const headers = new Headers(init.headers)
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  return fetch(`${API_URL}${path}`, { ...init, headers })
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function parseOrThrow<T>(
  response: Response,
  fallbackMessage: string,
): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : fallbackMessage
    throw new ApiError(response.status, detail)
  }
  return response.json() as Promise<T>
}

// --- Courses ---------------------------------------------------------

export interface CourseSummary {
  id: string
  title: string
  unit_count: number
  lesson_count: number
  tags: string[]
  owner_user_id: string | null
}

export type CourseDetail = Course & {
  tags: string[]
  owner_user_id: string | null
}

export async function listCourses(params?: {
  q?: string
  tag?: string
}): Promise<CourseSummary[]> {
  const query = new URLSearchParams()
  if (params?.q) query.set('q', params.q)
  if (params?.tag) query.set('tag', params.tag)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  const response = await authorizedFetch(`/api/courses${suffix}`)
  return parseOrThrow(response, 'Could not load courses.')
}

export async function getCourseFromApi(courseId: string): Promise<CourseDetail> {
  const response = await authorizedFetch(`/api/courses/${courseId}`)
  return parseOrThrow(response, 'Could not load this course.')
}

export async function createCourseOnApi(course: Course): Promise<CourseDetail> {
  const response = await authorizedFetch('/api/courses', {
    method: 'POST',
    body: JSON.stringify(course),
  })
  return parseOrThrow(response, 'Could not upload this course.')
}

export async function updateCourseTags(
  courseId: string,
  tags: string[],
): Promise<CourseSummary> {
  const response = await authorizedFetch(`/api/courses/${courseId}/tags`, {
    method: 'PATCH',
    body: JSON.stringify({ tags }),
  })
  return parseOrThrow(response, 'Could not update tags.')
}

// --- Progress ----------------------------------------------------------

export interface ProgressResponse {
  course_id: string
  completed_lesson_ids: string[]
}

export async function getProgress(courseId: string): Promise<ProgressResponse> {
  const response = await authorizedFetch(`/api/courses/${courseId}/progress`)
  return parseOrThrow(response, 'Could not load progress.')
}

export async function completeLesson(
  courseId: string,
  lessonId: string,
): Promise<void> {
  const response = await authorizedFetch(
    `/api/courses/${courseId}/progress/lessons/${lessonId}/complete`,
    { method: 'POST' },
  )
  await parseOrThrow(response, 'Could not save progress.')
}

// --- Course generation ---------------------------------------------------

export type GenerationJobStatus = 'pending' | 'running' | 'succeeded' | 'failed'

export interface GenerationJob {
  id: string
  status: GenerationJobStatus
  topic: string
  audience: string
  num_units: number
  lessons_per_unit: number
  course_id: string | null
  error: string | null
  created_at: string
  updated_at: string
}

export interface CreateGenerationJobInput {
  topic: string
  audience: string
  num_units: number
  lessons_per_unit: number
}

export async function createGenerationJob(
  input: CreateGenerationJobInput,
): Promise<GenerationJob> {
  const response = await authorizedFetch('/api/generation-jobs', {
    method: 'POST',
    body: JSON.stringify(input),
  })
  return parseOrThrow(response, 'Could not start course generation.')
}

export async function getGenerationJob(jobId: string): Promise<GenerationJob> {
  const response = await authorizedFetch(`/api/generation-jobs/${jobId}`)
  return parseOrThrow(response, 'Could not load generation job.')
}
