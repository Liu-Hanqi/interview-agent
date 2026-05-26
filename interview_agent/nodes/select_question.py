"""Select the next question from the current pool."""

import random
from pathlib import Path

from interview_agent.state import InterviewState


def _load_question_ids(pool: str) -> list[str]:
    qdir = Path(__file__).parent.parent / "questions" / pool
    if not qdir.exists():
        return []
    return [p.stem for p in qdir.glob("*.json")]


def select_next_question(state: InterviewState) -> InterviewState:
    pool = state["current_pool"]

    # For now, return a placeholder until real question bank is built
    # In Phase 1 this will read from questions/{pool}/*.json
    question_ids = _load_question_ids(pool)

    if not question_ids:
        # Return a generic warm-up question as fallback
        if pool == "algorithm":
            question = "实现一个函数，判断一个字符串是否是回文串。"
        elif pool == "fundamentals":
            question = "HashMap 和 HashTable 的区别是什么？"
        else:
            question = "你们系统的预加载策略是怎么设计的？什么条件下会触发刷新？"
    else:
        # Random pick from available questions
        chosen_id = random.choice(question_ids)
        # Load seed from file (Phase 1)
        question = f"[{chosen_id}]"  # placeholder

    state["current_question"] = question
    return state