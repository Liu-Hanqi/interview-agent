# Interview Agent

AI-powered interviewer with curiosity-driven dynamic follow-up questioning.

## Project Structure

```
interview-agent/
├── interview_agent/          # main package
│   ├── state.py              # InterviewState TypedDict
│   ├── graph.py              # LangGraph definition (Phase 3)
│   ├── nodes/                 # graph nodes (Phase 3)
│   ├── prompts/               # LLM prompt templates
│   ├── gate/                  # follow-up quality gate
│   ├── scoring/               # scoring engine
│   └── reporting/            # final report formatter
├── questions/                # question banks (Phase 1)
│   ├── algorithm/
│   ├── fundamentals/
│   └── scenario/
├── tests/                    # pytest test suite
├── scripts/                  # utilities
└── pyproject.toml
```

## Key Design Principles

- Follow-up loop cap: 10 total, with early termination
- Peak scoring: AI curiosity + candidate handles it = peak bonus
- Differentiating value gate: only HIGH DV follow-ups earn peak bonus
- No candidate LeetCode data exposed to AI interviewer

## Development

```bash
pip install -e .
pytest --collect-only
```