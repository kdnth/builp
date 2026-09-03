# Plan: AI course generation agent

This plan covers a LangChain/LangGraph agent that writes new courses, an
evaluation pipeline that checks the output, and RAG for optional source
material. It builds on the schema and backend we already have. It does not
require a new data model from scratch.

## Goal

Let a user type a topic and get a full, valid `Course` JSON document back.
The document must pass the same schema check we already use for course
upload (`backend/app/schemas/course.py`, mirrored on the frontend in
`frontend/src/schemas/course.ts`). Optionally, the user can attach source
material (PDFs, docs, notes) for the agent to draw from.

## Why reuse the existing schema

We already have a strict, tested schema for a course: units, lessons,
written content, code practice, and interactive activities. This schema is
the contract for the agent's output, not a new one. Two things follow:

- The agent's structured output binds directly to our existing Pydantic
  models (`Lesson`, `Unit`, code practice and activity types). No new
  translation layer.
- Every generated course goes through `POST /api/courses`, the same route
  a human-uploaded course goes through. Generation is just another way to
  produce input to a path we already trust.

## Pipeline shape

Use LangGraph, not a single open-ended agent loop. Course writing is a
known sequence of steps, not an open-ended tool-use problem. A graph gives
control over each step and makes each step easy to test on its own.

1. **Outline.** One call. Input: topic, audience level, number of units and
   lessons. Output: unit titles, lesson titles, and a one-line goal for
   each lesson. Small and cheap, so it's easy to regenerate if the shape
   is wrong before spending tokens on full content.

2. **Retrieval (if source material was given).** For each lesson, pull the
   most relevant chunks from the vector store. See the RAG section below.

3. **Lesson content generation.** One call per lesson (these can run in
   parallel, since lessons don't depend on each other once the outline
   exists). Output binds to our `Lesson` Pydantic model directly:
   `writtenLesson`, `codePractices`, `interactivePractices`. Retrieved
   chunks (if any) go into the prompt as grounding context.

4. **Validate and repair.** Run the automated checks from the evaluation
   section below. If something fails, send the specific failure back to
   the model and ask for a fix. Cap this at a small number of retries (for
   example, 2) so a bad generation fails cleanly instead of looping.

5. **Assemble.** Combine the outline and all lesson content into one
   `Course` document and run the full schema check one more time before
   it's treated as done.

## Evaluation pipeline

Three layers, from fast and automatic to slow and manual.

### 1. Structural checks (always run, no LLM call)

- Full schema validation, same as course upload.
- IDs are unique across the whole document.
- For `multipleChoice` activities, `correctIndex` is inside the `options`
  list.
- For `fillBlank` activities, the number of `{{blank}}` tokens in `text`
  matches the number of entries in `blanks`.
- For `function` code practices: run a model-written reference solution
  against the generated `testSuite` in a sandboxed subprocess. If the
  reference solution doesn't pass its own tests, the test cases are wrong,
  not the solution. This reuses the same execution approach already built
  for `FunctionPracticeView` (`runFunctionTests.ts`), just server-side.

A failure here goes back to step 4 of the pipeline (repair), not to a
human. These are cheap, deterministic, and safe to auto-retry.

### 2. LLM-as-judge checks (one call per lesson, after structural checks pass)

A separate grading call scores each lesson against a short rubric:

- Does the written lesson actually teach the thing the code practice
  tests?
- Is the difficulty right for the stated audience?
- In multiple choice, are the wrong options plausible, not obviously
  silly?
- Is the lesson free of factual errors (checked against retrieved source
  material, if any was given)?

Output: a 1-5 score per rubric item plus a short written note. Below a
score threshold, the course is marked for human review instead of
auto-published (see the review gate below).

### 3. Golden-set regression checks (offline, not per-generation)

A small, fixed set of topics with a known-good expected result, kept in
LangSmith as a dataset. Run this whenever the agent's prompts or pipeline
change, before shipping the change. This catches "we improved the prompt
for X and quietly broke Y." This is a check on the agent itself, run by a
developer, not something that happens on every user request.

## RAG for source material

- **Storage:** `pgvector` on the same Neon Postgres database we already
  use. No new database to run or pay for. LangChain has a built-in
  `PGVector` integration.
- **Ingestion:** user uploads files, we chunk them and store embeddings
  tied to a `source_set_id`. A course generation request can reference one
  source set. This keeps material for one course from leaking into
  another course's generation.
- **Retrieval:** plain top-k similarity search per lesson topic, scoped to
  the given `source_set_id`. Nothing fancier needed at this stage
  (re-ranking, hybrid search) until we see it's actually a problem.

## Data model additions

Small additions to what we already have, not a new system:

- `courses.status`: `draft` or `published`. Generated courses start as
  `draft`. A human moves a course to `published` after reviewing it (or
  it's promoted automatically if the LLM-as-judge score is high enough,
  once we trust that gate).
- `generation_jobs` table: id, status (`pending`, `running`, `succeeded`,
  `failed`), input (topic, audience, source_set_id), result (the course id
  once done), error (if failed). Generation can take a while (many LLM
  calls), so it should not block an HTTP request.
- `source_sets` and `source_chunks` tables for the RAG material: set id,
  owner, and per-chunk text plus embedding.

## API additions

- `POST /api/courses/generate` — starts a generation job, returns a job
  id right away. Runs the pipeline as a background task.
- `GET /api/generation-jobs/{id}` — poll status. On success, includes the
  new course id.
- `POST /api/source-sets` and file upload endpoints for RAG material,
  separate from course upload.

The frontend polls the job endpoint and shows progress (outline done,
writing lessons, checking work), similar in spirit to the existing course
upload page's error list, then routes to the new course once it's ready.

## Why a background job, not a request/response call

A multi-unit course means many LLM calls: one for the outline, one per
lesson for content, one per lesson for grading. This will not finish
inside a normal request timeout. A simple job table plus
`BackgroundTasks` is enough at our current scale. A real queue (Celery,
Redis, etc.) is a later upgrade if generation volume grows, not a
day-one requirement.

## Suggested build order

1. Structural checks first, as a standalone module, tested against the
   existing sample course and against deliberately broken documents. This
   has value even before the agent exists (it's useful for any future
   automated course editing too).
2. Outline generation, with the check-and-repair loop wired to the
   structural checks from step 1.
3. Single-lesson content generation, with the checks passing on real
   output before moving on.
4. Wire lessons to run in parallel, assemble the full course, run the
   final check.
5. Add the LLM-as-judge grading step and the `draft`/`published` gate.
6. Add RAG: ingestion, `pgvector` storage, retrieval wired into lesson
   generation.
7. Set up the golden-set dataset in LangSmith and run it before any future
   prompt change ships.

Steps 1 to 4 alone are enough to demo a working generator. RAG and the
judge step can come after, since the structural checks already guarantee
every generated course is at least valid and runnable.
