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
  language: z.enum(['javascript', 'python']).default('javascript'),
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
  term: z.string().min(1).max(60),
  definition: z.string().min(1).max(150),
})

const matchingActivitySchema = z.object({
  type: z.literal('matching'),
  id: z.string().min(1),
  description: z.string().nullish(),
  explanation: z.string().nullish(),
  pairs: z.array(matchingPairSchema).min(1),
})

const blankSchema = z.object({
  position: z.number().int().min(0),
  accepted: z.array(z.string().min(1)).min(1),
})

const fillBlankActivitySchema = z.object({
  type: z.literal('fillBlank'),
  id: z.string().min(1),
  description: z.string().nullish(),
  explanation: z.string().nullish(),
  text: z.string().min(1),
  blanks: z.array(blankSchema).min(1),
})

const multipleChoiceActivitySchema = z.object({
  type: z.literal('multipleChoice'),
  id: z.string().min(1),
  description: z.string().nullish(),
  explanation: z.string().nullish(),
  passage: z.string().nullish(),
  question: z.string().min(1),
  options: z.array(z.string().min(1)).min(2),
  optionExplanations: z.array(z.string()).nullish(),
  correctIndex: z.number().int().min(0),
})

const orderingActivitySchema = z.object({
  type: z.literal('ordering'),
  id: z.string().min(1),
  description: z.string().nullish(),
  explanation: z.string().nullish(),
  basis: z.string().min(1),
  items: z.array(z.string().min(1)).min(3).max(8),
})

const categorizeActivitySchema = z.object({
  type: z.literal('categorize'),
  id: z.string().min(1),
  description: z.string().nullish(),
  explanation: z.string().nullish(),
  categories: z.array(z.string().min(1)).min(2).max(4),
  items: z
    .array(
      z.object({
        id: z.string().min(1),
        text: z.string().min(1),
        category: z.string().min(1),
      }),
    )
    .min(3)
    .max(8),
})

const numericActivitySchema = z.object({
  type: z.literal('numeric'),
  id: z.string().min(1),
  description: z.string().nullish(),
  explanation: z.string().nullish(),
  question: z.string().min(1),
  answer: z.number(),
  tolerance: z.number().min(0).default(0),
  unit: z.string().nullish(),
})

const interactiveActivitySchema = z.discriminatedUnion('type', [
  matchingActivitySchema,
  fillBlankActivitySchema,
  multipleChoiceActivitySchema,
  orderingActivitySchema,
  categorizeActivitySchema,
  numericActivitySchema,
])

const interactivePracticeSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  activities: z.array(interactiveActivitySchema).min(1),
})

const lessonPageSchema = z.discriminatedUnion('kind', [
  z.object({ kind: z.literal('written'), written: writtenLessonSchema }),
  z.object({ kind: z.literal('code'), practice: codePracticeSchema }),
  z.object({
    kind: z.literal('interactive'),
    practice: interactivePracticeSchema,
  }),
])

const lessonSchema = z
  .object({
    id: z.string().min(1),
    title: z.string().min(1),
    pages: z.array(lessonPageSchema).min(1).optional(),
    writtenLesson: writtenLessonSchema.optional(),
    codePractices: z.array(codePracticeSchema).default([]),
    interactivePractices: z.array(interactivePracticeSchema).default([]),
  })
  .refine((lesson) => lesson.pages || lesson.writtenLesson, {
    message: 'a lesson needs pages, or a writtenLesson',
  })

const unitSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  lessons: z.array(lessonSchema).min(1),
})

export const courseSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  courseType: z.enum(['programming', 'general']).default('programming'),
  units: z.array(unitSchema).min(1),
  forkedFromId: z.string().min(1).nullable().optional(),
})

export type CourseInput = z.infer<typeof courseSchema>

export const courseJsonSchema = z.toJSONSchema(courseSchema, { io: 'input' })
