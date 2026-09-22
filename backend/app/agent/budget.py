"""A hard, whole-job token ceiling.

Without this, a job that can't converge (an overview that keeps returning
more units than asked for, a lesson that keeps failing its checks) has no
limit on how much it can spend: it will keep retrying and fanning out
until every branch finishes on its own. One run of the golden set hit an
org-wide spend limit on the third of eight topics because of exactly this
- a single "1 unit" request silently grew to 6 units before anything
stopped it.

The cap is sized from what was actually requested (units x lessons), not
from whatever the model decides to generate, so a job that balloons past
its own request hits the ceiling almost immediately instead of running to
whatever size the model chose.
"""

import os
from threading import Lock

from app.agent.llm import CallUsage

DEFAULT_SCREENING_TOKENS = 5_000
DEFAULT_UNIT_TOKENS = 40_000
DEFAULT_LESSON_TOKENS = 90_000


class TokenBudgetExceeded(Exception):
    def __init__(self, spent: int, limit: int):
        self.spent = spent
        self.limit = limit
        super().__init__(
            f"Generation stopped: used {spent:,} tokens, over the {limit:,} "
            "token budget for this job."
        )


class TokenBudget:
    """One counter shared by every call in a job. Parallel branches all
    report to it, so the first call to cross the limit stops the job,
    regardless of which branch it was in."""

    def __init__(self, limit: int):
        self.limit = limit
        self._spent = 0
        self._lock = Lock()

    @property
    def spent(self) -> int:
        with self._lock:
            return self._spent

    def record(self, usage: CallUsage) -> None:
        spent_tokens = usage.input_tokens + usage.output_tokens
        spent_tokens += usage.cache_creation_tokens
        with self._lock:
            self._spent += spent_tokens
            if self._spent > self.limit:
                raise TokenBudgetExceeded(self._spent, self.limit)


def _env_int(name: str, default: int) -> int:
    override = os.getenv(name)
    if override and override.strip():
        return int(override.strip())
    return default


def job_token_budget(num_units: int, lessons_per_unit: int) -> int:
    """The token ceiling for one job, sized from what was requested.

    Each constant is a generous per-unit or per-lesson allowance, generous
    enough to cover a few retries with tier escalation on a compliant
    request. It is not a precise cost model. Override via env vars using the
    same convention as COURSE_GEN_MODEL_* in app/agent/llm.py.
    """
    screening = _env_int("COURSE_GEN_TOKEN_BUDGET_SCREENING", DEFAULT_SCREENING_TOKENS)
    per_unit = _env_int("COURSE_GEN_TOKEN_BUDGET_PER_UNIT", DEFAULT_UNIT_TOKENS)
    per_lesson = _env_int("COURSE_GEN_TOKEN_BUDGET_PER_LESSON", DEFAULT_LESSON_TOKENS)
    return screening + per_unit * num_units + per_lesson * num_units * lessons_per_unit
