import type { Course, CourseType } from '../types/course'
import type { CodeLanguage } from '../types/codeLanguage'
import { getJWTToken } from './auth'

const RAW_API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? ''

function normalizeApiBaseUrl(value: string): string {
  const trimmed = value.trim()
  if (!trimmed) {
    return ''
  }
  const withoutTrailingSlash = trimmed.replace(/\/+$/, '')
  // Most routes in this app already include a leading /api segment; trim an
  // accidentally configured base ".../api" to avoid ".../api/api/..." 404s.
  return withoutTrailingSlash.replace(/\/api$/, '')
}

const API_URL = normalizeApiBaseUrl(RAW_API_URL)

function buildApiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return API_URL ? `${API_URL}${normalizedPath}` : normalizedPath
}

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
  return fetch(buildApiUrl(path), { ...init, headers })
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

function detailEntryMessage(detail: unknown): string | null {
  if (!detail || typeof detail !== 'object') {
    return null
  }
  const record = detail as Record<string, unknown>
  const msg = typeof record.msg === 'string' ? record.msg.trim() : ''
  if (!msg) {
    return null
  }

  if (Array.isArray(record.loc)) {
    const fieldPath = record.loc
      .filter((segment) => typeof segment === 'string')
      .join('.')
      .trim()
    if (fieldPath) {
      return `${fieldPath}: ${msg}`
    }
  }
  return msg
}

function extractApiErrorMessage(body: unknown): string | null {
  if (!body || typeof body !== 'object') {
    return null
  }
  const record = body as Record<string, unknown>

  const detail = record.detail
  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  if (Array.isArray(detail)) {
    for (const entry of detail) {
      if (typeof entry === 'string' && entry.trim()) {
        return entry
      }
      const parsed = detailEntryMessage(entry)
      if (parsed) {
        return parsed
      }
    }
  }

  if (detail && typeof detail === 'object') {
    const detailRecord = detail as Record<string, unknown>
    if (
      typeof detailRecord.message === 'string' &&
      detailRecord.message.trim()
    ) {
      return detailRecord.message
    }
    if (typeof detailRecord.error === 'string' && detailRecord.error.trim()) {
      return detailRecord.error
    }
  }

  if (typeof record.message === 'string' && record.message.trim()) {
    return record.message
  }
  return null
}

function tryParseJson(value: string): unknown | null {
  try {
    return JSON.parse(value) as unknown
  } catch {
    return null
  }
}

function extractPlainTextError(bodyText: string): string | null {
  const trimmed = bodyText.trim()
  if (!trimmed) {
    return null
  }

  const plainText = trimmed
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()

  if (!plainText) {
    return null
  }
  return plainText.slice(0, 240)
}

function responsePath(response: Response): string | null {
  if (!response.url) {
    return null
  }
  try {
    return new URL(response.url).pathname
  } catch {
    return null
  }
}

async function ensureOk(
  response: Response,
  fallbackMessage: string,
): Promise<void> {
  if (response.ok) {
    return
  }
  const bodyText = await response.text().catch(() => '')
  const body = bodyText ? tryParseJson(bodyText) : null
  const plainTextError = body ? null : extractPlainTextError(bodyText)
  const path = responsePath(response)
  const pathHint = path ? ` at ${path}` : ''
  const apiHint =
    !API_URL && response.status === 404
      ? ' Set VITE_API_URL if frontend and backend are on different hosts.'
      : ''
  const detail =
    extractApiErrorMessage(body) ??
    plainTextError ??
    `${fallbackMessage} (HTTP ${response.status}${pathHint}).`
  throw new ApiError(response.status, `${detail}${apiHint}`)
}

async function parseOrThrow<T>(
  response: Response,
  fallbackMessage: string,
): Promise<T> {
  await ensureOk(response, fallbackMessage)
  return response.json() as Promise<T>
}

// For endpoints that respond with no body (204 No Content). Never calls
// response.json() - unlike parseOrThrow, that's not a fallback for an empty
// body, it's simply not part of this function's contract.
async function parseVoidOrThrow(
  response: Response,
  fallbackMessage: string,
): Promise<void> {
  await ensureOk(response, fallbackMessage)
}

// --- Courses ---------------------------------------------------------

export interface CourseSummary {
  id: string
  title: string
  course_type: CourseType
  unit_count: number
  lesson_count: number
  tags: string[]
  owner_user_id: string | null
  saved: boolean
}

export interface PaginatedCourses {
  items: CourseSummary[]
  total: number
}

export type CourseDetail = Course & {
  tags: string[]
  owner_user_id: string | null
  saved: boolean
}

export async function listCourses(params?: {
  q?: string
  tag?: string
  courseType?: CourseType
  ownerUserId?: string
  // "My Courses" membership: owned by this user OR saved by them.
  forUserId?: string
  limit?: number
  offset?: number
}): Promise<PaginatedCourses> {
  const query = new URLSearchParams()
  if (params?.q) query.set('q', params.q)
  if (params?.tag) query.set('tag', params.tag)
  if (params?.courseType) query.set('course_type', params.courseType)
  if (params?.ownerUserId) query.set('owner_user_id', params.ownerUserId)
  if (params?.forUserId) query.set('for_user_id', params.forUserId)
  if (params?.limit != null) query.set('limit', String(params.limit))
  if (params?.offset != null) query.set('offset', String(params.offset))
  const suffix = query.toString() ? `?${query.toString()}` : ''
  const response = await authorizedFetch(`/api/courses${suffix}`)
  return parseOrThrow(response, 'Could not load courses.')
}

export async function saveCourse(courseId: string): Promise<void> {
  const response = await authorizedFetch(`/api/courses/${courseId}/save`, {
    method: 'POST',
  })
  return parseVoidOrThrow(response, 'Could not save this course.')
}

export async function unsaveCourse(courseId: string): Promise<void> {
  const response = await authorizedFetch(`/api/courses/${courseId}/save`, {
    method: 'DELETE',
  })
  return parseVoidOrThrow(response, 'Could not unsave this course.')
}

export async function getCourseFromApi(
  courseId: string,
): Promise<CourseDetail> {
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

export async function deleteCourse(courseId: string): Promise<void> {
  const response = await authorizedFetch(`/api/courses/${courseId}`, {
    method: 'DELETE',
  })
  return parseVoidOrThrow(response, 'Could not delete this course.')
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

export type GenerationJobStatus =
  'pending' | 'running' | 'succeeded' | 'failed' | 'refused'
export type GenerationStage =
  'screening' | 'outline' | 'units' | 'lessons' | 'assembling'
export type CodePracticeChoice = CodeLanguage | 'none' | 'auto'
export type LearnerLevel = 'beginner' | 'intermediate' | 'advanced'
export type ReadingStyle = 'single' | 'interleaved'

export interface GenerationJob {
  id: string
  status: GenerationJobStatus
  topic: string
  audience: string
  num_units: number
  lessons_per_unit: number
  course_type: CourseType
  language: CodePracticeChoice
  learning_goals: string | null
  level: LearnerLevel
  notes: string | null
  reading_style: ReadingStyle
  stage: GenerationStage | null
  lessons_total: number | null
  lessons_completed: number
  course_id: string | null
  error: string | null
  refusal_category: string | null
  refusal_reason: string | null
  created_at: string
  updated_at: string
}

interface SharedCreateGenerationJobInput {
  topic: string
  audience: string
  num_units: number
  lessons_per_unit: number
  course_type: CourseType
  language: CodePracticeChoice
  learning_goals?: string | null
  level: LearnerLevel
  notes?: string | null
}

export type GenerationMode = 'free_credit' | 'provider_api_key'
export type SupportedGenerationProvider = 'anthropic'

export type CreateGenerationJobInput =
  | (SharedCreateGenerationJobInput & {
      generation_mode: 'free_credit'
      provider?: never
      provider_api_key?: never
    })
  | (SharedCreateGenerationJobInput & {
      generation_mode: 'provider_api_key'
      provider: SupportedGenerationProvider
      provider_api_key: string
    })

export async function createGenerationJob(
  input: CreateGenerationJobInput,
): Promise<GenerationJob> {
  const response = await authorizedFetch('/api/generation-jobs', {
    method: 'POST',
    body: JSON.stringify(input),
  })
  return parseOrThrow(response, 'Could not start course generation.')
}

export async function listGenerationJobs(): Promise<GenerationJob[]> {
  const response = await authorizedFetch('/api/generation-jobs')
  return parseOrThrow(response, 'Could not load generation jobs.')
}

export async function getGenerationJob(jobId: string): Promise<GenerationJob> {
  const response = await authorizedFetch(`/api/generation-jobs/${jobId}`)
  return parseOrThrow(response, 'Could not load generation job.')
}
