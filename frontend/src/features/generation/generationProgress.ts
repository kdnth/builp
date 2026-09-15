import type { GenerationJob, GenerationStage } from '../../lib/api'

const STAGE_LABELS: Record<GenerationStage, string> = {
  outline: 'Planning the course',
  units: 'Outlining units',
  lessons: 'Writing lessons',
  assembling: 'Putting it together',
}

const SHORT_STAGE_LABELS: Record<GenerationStage, string> = {
  outline: 'Planning',
  units: 'Outlining',
  lessons: 'Writing',
  assembling: 'Finishing',
}

export function isActiveJob(job: GenerationJob) {
  return job.status === 'pending' || job.status === 'running'
}

function lessonCounts(job: GenerationJob) {
  if (job.stage !== 'lessons' || !job.lessons_total) return null
  return {
    done: Math.min(job.lessons_completed, job.lessons_total),
    total: job.lessons_total,
  }
}

export function progressLabel(job: GenerationJob) {
  if (job.status === 'pending') return 'Queued'
  if (job.status === 'succeeded') return 'Done'
  if (job.status === 'failed') return 'Failed'
  return job.stage ? STAGE_LABELS[job.stage] : 'Starting'
}

export function shortProgressLabel(job: GenerationJob) {
  const counts = lessonCounts(job)
  if (counts) return `${counts.done}/${counts.total} lessons`
  if (job.status === 'pending') return 'Queued'
  return job.stage ? SHORT_STAGE_LABELS[job.stage] : 'Starting'
}

export function lessonProgressText(job: GenerationJob) {
  const counts = lessonCounts(job)
  return counts ? `${counts.done} of ${counts.total} lessons written` : null
}

export function progressPercent(job: GenerationJob) {
  if (job.status === 'succeeded') return 100
  if (job.status === 'pending' || !job.stage) return 2
  switch (job.stage) {
    case 'outline':
      return 5
    case 'units':
      return 10
    case 'lessons': {
      const counts = lessonCounts(job)
      return counts ? 10 + (85 * counts.done) / counts.total : 10
    }
    case 'assembling':
      return 97
  }
}
