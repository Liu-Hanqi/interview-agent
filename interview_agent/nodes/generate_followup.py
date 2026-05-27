"""Generate a follow-up question based on the candidate's last answer."""

import json

from interview_agent.llm import generate
from interview_agent.prompts import render
from interview_agent.state import InterviewState, Turn


def _format_history(history: list[Turn]) -> str:
    if not history:
        return "(无历史记录)"
    lines = []
    for i, turn in enumerate(history, 1):
        lines.append(f"Q{i}: {turn.get('question', '')}")
        lines.append(f"A{i}: {turn.get('answer', '')}")
    return "\n".join(lines)


def _parse_json_response(raw: str) -> dict:
    """Parse JSON from LLM response, handling non-JSON and partial responses."""
    import re

    text = raw.strip()
    if not text:
        return {}

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract JSON from markdown code fences
    match = re.search(r"```json\s*(\{.*\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # Try broader extraction — find first { to last }
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return {}


def generate_followup(state: InterviewState) -> InterviewState:
    history: list[Turn] = state.get("history", [])
    last_question = state.get("current_question", "")
    last_answer = history[-1]["answer"] if history else ""

    anchors = state.get("_current_anchors", "预加载机制、刷新策略、缓存一致性")
    history_text = _format_history(history)
    followup_count = state.get("followup_count", 0)

    system, user = render(
        "followup_generator",
        "请生成追问",
        current_question=last_question,
        candidate_answer=last_answer,
        history=history_text,
        knowledge_anchors=anchors,
        followup_count=followup_count,
    )

    resp = generate(system=system, user=user, model="claude-sonnet", json_mode=True)
    result = _parse_json_response(resp.raw)

    followup_text = result.get("followup", "")
    direction = result.get("direction", "depth")
    should_stop = result.get("should_stop", False)
    anchor_hit = result.get("knowledge_anchor_hit", [])

    # Store follow-up metadata in the last turn
    if history:
        history[-1]["followups"].append(followup_text)
        # Store direction on the turn for later gate/score access
        history[-1]["_followup_direction"] = direction
        history[-1]["_anchor_hit"] = anchor_hit

    state["current_question"] = followup_text
    state["followup_count"] = followup_count + 1
    state["total_followups"] = state.get("total_followups", 0) + 1
    # Signal early stop if followup generation decided to stop
    state["_should_stop_after_answer"] = should_stop

    return state