# CLAUDE.md — Interview Agent

## Project Overview

AI面试官，开源核心推理引擎。Python + LangGraph + 自定义评分引擎。MIT协议，商用需联系作者。

## Key Design Decisions

- Follow-up loop cap: 10 total, with early termination
- Gate evaluation runs in parallel with scoring (same node)
- Gate uses claude-3-haiku; question generation uses claude-3-7-sonnet
- Question banks: algorithm (10%) / fundamentals (50%) / scenario (40%)
- Scenario questions: two categories only — "foundation" and "business"

## Architecture (per ARCHITECTURE.md)

- LangGraph graph nodes: select_question → ask_question → receive_answer → should_followup → generate_followup → score_answer → advance_pool → compile_report
- Follow-up quality gate: is_followup_worth_scoring() — second LLM call tags DV=HIGH/LOW
- Peak bonus: +5 per successful follow-up chain (HIGH DV only)

## Question Bank Format

```json
{
  "id": "py-foundation-001",
  "pool": "fundamentals",
  "category": "async",
  "difficulty": "medium",
  "seed": "How does Python's asyncio actually schedule goroutines under the hood?",
  "knowledge_anchors": ["event loop", "Future / Task"],
  "depth_trigger_pattern": "candidate mentions 'event loop' without prompting",
  "expected_depth": 2
}
```

## Conventions

- All LLM calls go through `anthropic` client (configured via ANTHROPIC_API_KEY env var)
- State is kept in-memory during interview; no persistence in v1
- Prompts stored as `.txt` files in `prompts/`
- Score values are floats; final report computes weighted sum

## Before Writing Code

- Read ARCHITECTURE.md first
- Keep prompts in `prompts/` as `.txt` files — no hardcoded prompt strings in code
- Run `pytest --collect-only` after creating new test files