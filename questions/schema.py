from typing import TypedDict, Literal


class Question(TypedDict, total=False):
    id: str
    pool: Literal["algorithm", "fundamentals", "scenario"]
    category: str
    difficulty: Literal["easy", "medium", "hard"]
    seed: str
    knowledge_anchors: list[str]
    # 以下字段仅 scenario 有
    depth_trigger_pattern: str | None
    expected_depth: int | None
    typical_duration_rounds: int | None


def validate_question(data: dict) -> list[str]:
    """返回缺失的必填 key 列表，空列表=校验通过"""
    required = {"id", "pool", "category", "difficulty", "seed", "knowledge_anchors"}
    return list(required - set(data.keys()))