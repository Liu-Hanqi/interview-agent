"""State definitions and types for the interview agent graph."""

from typing import TypedDict


class Turn(TypedDict, total=False):
    """A single question-answer turn in the interview.

    total=False: allows extra keys at runtime for internal use.
    """

    question: str
    answer: str
    followups: list[str]
    differentiating_value: str  # "HIGH" | "LOW"

    # Runtime-only keys (not persisted)
    _followup_direction: str
    _anchor_hit: list[str]
    _dv_score: str  # "HIGH" | "LOW" set by gate


class ScoreDelta(TypedDict):
    """Score change from a single turn."""

    dimension: str  # "clarity" | "depth" | "tradeoffs" | "honesty" | "design"
    value: float
    reason: str


class InterviewState(TypedDict, total=False):
    """Full state carried through the interview graph.

    total=False: allows extra keys at runtime for internal use.
    """

    history: list[Turn]
    current_pool: str  # "algorithm" | "fundamentals" | "scenario"
    followup_count: int
    total_followups: int
    scores: list[ScoreDelta]
    candidate_profile: str  # job description context
    current_question: str | None
    pending_answer: str | None

    # Runtime-only keys (not persisted between nodes)
    _current_anchors: str
    _should_stop_after_answer: bool
    _last_dv: str  # "HIGH" | "LOW"
    _peak_bonus: int