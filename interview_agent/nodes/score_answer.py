"""Score the candidate's answer using LLM evaluation."""

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


def _parse_score(raw: str) -> dict:
    text = raw.strip()
    for fence in ("```json", "```JSON", "```"):
        if text.startswith(fence):
            text = text[len(fence) :]
        if text.endswith(fence):
            text = text[:-len(fence)]
    return json.loads(text.strip())


def score_answer(state: InterviewState) -> InterviewState:
    """Evaluate the last answer and compute a score delta.

    Gate and scoring run in parallel in the same node.
    """
    history: list[Turn] = state.get("history", [])
    if not history:
        return state

    last_turn = history[-1]
    current_question = state.get("current_question", "")
    last_answer = last_turn.get("answer", "")

    # Determine if this is a follow-up round (has followups list populated)
    is_followup = bool(last_turn.get("followups", []))
    followup_text = last_turn["followups"][-1] if is_followup else "N/A"

    history_text = _format_history(history[:-1])  # exclude current turn

    # --- Parallel Gate + Score calls ---
    # Gate: is this follow-up HIGH DV?
    gate_system, gate_user = render(
        "gate_evaluator",
        "评估追问质量",
        current_question=current_question,
        candidate_answer=last_answer,
        followup=followup_text,
    )
    gate_resp = generate(
        system=gate_system,
        user=gate_user,
        model="claude-haiku",
        json_mode=True,
    )
    gate_result = _parse_score(gate_resp.raw)
    dv = gate_result.get("differentiating_value", "LOW")

    # Score: evaluate this answer
    score_system, score_user = render(
        "score_answer",
        "评估候选人回答",
        current_question=current_question,
        candidate_answer=last_answer,
        history=history_text,
        followup=followup_text,
    )
    score_resp = generate(
        system=score_system,
        user=score_user,
        model="claude-sonnet",
        json_mode=True,
    )
    score_result = _parse_score(score_resp.raw)

    # Aggregate scores
    score_delta = score_result.get("score_delta", {})
    scores = state.get("scores", [])

    for dim, data in score_delta.items():
        if isinstance(data, dict):
            scores.append({
                "dimension": dim,
                "value": data.get("value", 0.0),
                "reason": data.get("reason", ""),
            })

    # Peak bonus: HIGH DV follow-up that was handled
    peak_bonus = 0
    if dv == "HIGH" and score_result.get("peak_triggered"):
        peak_bonus = 5
        scores.append({
            "dimension": "peak_bonus",
            "value": 5.0,
            "reason": f"HIGH DV追问被接住：{followup_text[:30]}...",
        })

    # Update state
    state["scores"] = scores
    state["_last_dv"] = dv
    state["_peak_bonus"] = peak_bonus
    last_turn["differentiating_value"] = dv

    return state