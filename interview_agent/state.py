"""State definitions and types for the interview agent graph."""

from typing import TypedDict


class Turn(TypedDict):
    """A single question-answer turn in the interview."""

    question: str
    answer: str
    followups: list[str]
    differentiating_value: str  # "HIGH" | "LOW"


class ScoreDelta(TypedDict):
    """Score change from a single turn."""

    dimension: str  # "clarity" | "depth" | "tradeoffs" | "honesty" | "design"
    value: float
    reason: str


class InterviewState(TypedDict):
    """Full state carried through the interview graph."""

    history: list[Turn]
    current_pool: str  # "algorithm" | "fundamentals" | "scenario"
    followup_count: int
    total_followups: int
    scores: list[ScoreDelta]
    candidate_profile: str  # job description context
    current_question: str | None
    pending_answer: str | None