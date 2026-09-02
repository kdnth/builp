import { z } from 'zod'

const testCaseSchema = z.object({
  input: z.array(z.unknown()),
  expectedOutput: z.unknown(),
})

const writtenLessonSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  markdown: z.string(),
})

const functionCodePracticeSchema = z.object({
  type: z.literal('function'),
  id: z.string().min(1),
  title: z.string().min(1),
  functionSignature: z.string().min(1),
  description: z.string(),
  testSuite: z.array(testCaseSchema).min(1),
})

const componentCodePracticeSchema = z.object({
  type: z.literal('component'),
  id: z.string().min(1),
  title: z.string().min(1),
  starterFiles: z.record(z.string(), z.string()),
  dependencies: z.record(z.string(), z.string()),
})

const codePracticeSchema = z.discriminatedUnion('type', [
  functionCodePracticeSchema,
  componentCodePracticeSchema,
])

const matchingPairSchema = z.object({
  id: z.string().min(1),
  term: z.string().min(1),
  definition: z.string().min(1),
})

const matchingActivitySchema = z.object({
  type: z.literal('matching'),
  id: z.string().min(1),
  description: z.string().optional(),
  pairs: z.array(matchingPairSchema).min(1),
})

const blankSchema = z.object({
  position: z.number().int().min(0),
  accepted: z.array(z.string().min(1)).min(1),
})

const fillBlankActivitySchema = z.object({
  type: z.literal('fillBlank'),
  id: z.string().min(1),
  description: z.string().optional(),
  text: z.string().min(1),
  blanks: z.array(blankSchema).min(1),
})

const multipleChoiceActivitySchema = z.object({
  type: z.literal('multipleChoice'),
  id: z.string().min(1),
  description: z.string().optional(),
  question: z.string().min(1),
  options: z.array(z.string().min(1)).min(2),
  correctIndex: z.number().int().min(0),
})

const interactiveActivitySchema = z.discriminatedUnion('type', [
  matchingActivitySchema,
  fillBlankActivitySchema,
  multipleChoiceActivitySchema,
])

const interactivePracticeSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  activities: z.array(interactiveActivitySchema).min(1),
})

const lessonSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  writtenLesson: writtenLessonSchema,
  codePractices: z.array(codePracticeSchema),
  interactivePractices: z.array(interactivePracticeSchema),
})

const unitSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  lessons: z.array(lessonSchema).min(1),
})

export const courseSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  units: z.array(unitSchema).min(1),
})

export type CourseInput = z.infer<typeof courseSchema>

export const courseJsonSchema = z.toJSONSchema(courseSchema)
