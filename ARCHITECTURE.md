# Interview Agent — Architecture Design

## 1. Product Positioning

**What it is**: An AI interviewer that evaluates Python backend candidates through curiosity-driven dynamic questioning.

**What it is NOT**: A question bank lookup tool. The AI does not retrieve fixed questions — it generates questions and follow-ups dynamically based on candidate responses.

**Target users**: Python backend developers preparing for real interviews. The first user is the author.

---

## 2. Question Bank Structure

Three independent pools, each with a weight in final scoring:

| Pool | Weight | Sourcing | Selection |
|------|--------|----------|-----------|
| Algorithm | 10% | Crawl LeetCode open problems | Random by difficulty tag |
| Fundamentals (八股文) | 50% | Crawl open GitHub repos | Random by category |
| Scenario | 40% | **Self-authored** high-quality problems | **Curiosity-driven** — AI picks based on context |

### Scenario Pool Categories

Two top-level categories only — **no fine-grained subcategories** (e.g., Kafka vs RocketMQ are both "Message Queue" and do not need separate treatment):

- **Foundation** — multi-threading, concurrency, async, caching, message queues, distributed systems, performance
- **Business** — booking flow, inventory management, supplier integration, price calculation, order state machines

Each problem has:
- A seed question (open-ended)
- Expected knowledge anchors (things a senior candidate should mention unprompted)
- A "depth trigger" — the conversation pattern that signals the AI should dig deeper

### Question Bank Seeding Sources

Initial question banks are sourced from freely-available open references:

| Pool | Source | URL | Coverage |
|------|--------|-----|----------|
| Fundamentals | JavaGuide (Java基础常见面试题总结) | https://javaguide.cn/java/basis/java-basic-questions-01.html | 基础概念、语法、基本数据类型、变量、方法；可扩展至 javaguide.cn/java/basis/ (并发、集合、JVM、IO) |
| Fundamentals / Scenario | 小林coding (图解网络) | https://www.xiaolincoding.com/network/ | 20W字+500图. TCP/UDP/HTTP/HTTPS/网络层；映射至 foundation 分类 |

Additional crawling targets (future phases):
- javaguide.cn/java/basis/java-basic-questions-02.html
- javaguide.cn/java/basis/java-concurrent-questions.html
- xiaolincoding.com (Redis/MySQL/系统设计)
- GitHub: free-programming-resources (multi-language fundamentals)

All crawled content is converted to the JSON format defined in Section 6 before storage.

---

## 3. Scoring Architecture

### Per-Turn Scoring

After every candidate answer, the AI produces a score signal:

```
score_delta = {
    "dimension": "clarity | depth | tradeoffs | honesty | design",
    "value": float,   # positive =加分, negative =扣分
    "reason": str,    # one-line explanation
}
```

### Final Score Composition

| Dimension | Max Points |
|-----------|-----------|
| Algorithm (10%) | 10 |
| Fundamentals (50%) | 50 |
| Scenario (40%) | 40 |
| **Total** | **100** |

### Peak Scoring (Scenario Layer)

The "peak theorem" applies only to scenario questions:

- **Baseline**: candidate answers, AI scores it normally
- **Peak trigger**: AI generates a follow-up question AND the candidate handles it well
  - Each successful follow-up chain multiplies the scenario score: +5 per additional round
  - **Cap**: after 10 rounds total (initial question + up to 9 follow-ups), the chain is considered exhausted
- **Decay**: if the candidate fumbles a follow-up, no peak bonus for that chain

### Consistency Constraint

AI-generated follow-ups carry an implicit **differentiating value** (DV) tag:
- **High DV**: only senior candidates (3+ years) would handle it well → peak bonus applies
- **Low DV**: any competent developer would answer this → no peak bonus even if answered correctly

The AI tags each follow-up with DV before scoring, so the same conversation evaluated by different AI runs produces consistent results.

---

## 4. Core Agent Architecture (LangGraph)

```
State: {
    history: list[Turn],           # all Q&A so far
    current_pool: str,            # "algorithm" | "fundamentals" | "scenario"
    followup_count: int,          # starts at 0 per topic
    total_followups: int,         # global cap = 10
    scores: list[ScoreDelta],
    candidate_profile: str,       # job description context
}
```

### Graph Nodes

```
graph nodes:
  1. select_next_question  — picks next question from current pool
  2. ask_question          — renders question to candidate
  3. receive_answer       — stores candidate reply in history
  4. should_followup      — decides if a follow-up is warranted (branch on followup_count < 10)
  5. generate_followup     — produces follow-up + differentiating_value tag
  6. score_answer         — emits ScoreDelta
  7. advance_pool         — moves to next pool when current is exhausted
  8. compile_report       — builds final structured report
```

### Graph Edges (key transitions)

```
select_next_question
    → ask_question
        → receive_answer
            → should_followup
                ├─ [YES, followup_count < 10] → generate_followup
                │                                    → ask_question (loop)
                └─ [NO or count >= 10] → score_answer
                                             → advance_pool / compile_report
```

### Follow-up Loop Invariant

The loop `generate_followup → ask_question → receive_answer → should_followup` runs at most **10 times total** across all topics combined. When `total_followups >= 10`, the agent stops asking follow-ups and scores whatever has been collected.

**Early termination** — the loop may end early if:
- The candidate fails to handle a follow-up (fumble point reached — no peak bonus for this chain)
- The AI determines the current topic has been fully explored (all key knowledge anchors covered)
- The candidate explicitly signals they want to move on

**Gate latency control** — the follow-up quality gate is the main latency risk. Three mitigations:
1. Run gate evaluation in **parallel** with scoring (same turn, not sequential)
2. Use `claude-3-haiku` for gate calls (fast, cheap) vs `claude-3-7-sonnet` for question generation
3. Cache gate decisions for semantically identical follow-up patterns across runs

---

## 5. Follow-up Quality Filter

Before a generated follow-up is shown to the candidate, it passes a gate:

```
gate: is_followup_worth_scoring(followup, conversation_history) → bool
```

This is implemented as a **second LLM call** (same model, separate prompt) that evaluates:
1. Does this follow-up probe something genuinely deeper than what was just answered?
2. Would a junior candidate (1-year) answer this the same way as a senior?
3. Is this a known high-frequency interview topic?

If all three are YES → pass the gate, assign `differentiating_value = HIGH`
If any is NO → pass the gate with `differentiating_value = LOW` (no peak bonus even if answered correctly)

This gate is the **consistency mechanism**: it prevents the AI from asking trivially-followable questions just to rack up peak scores.

---

## 6. Question Bank Format

Each question is a JSON file:

```json
{
  "id": "py-foundation-001",
  "pool": "fundamentals",
  "category": "async",
  "difficulty": "medium",
  "seed": "How does Python's asyncio actually schedule goroutines under the hood?",
  "knowledge_anchors": [
    "event loop",
    "Future / Task",
    "awaitable",
    "gather / create_task"
  ],
  "depth_trigger_pattern": "candidate mentions 'event loop' without prompting",
  "expected_depth": 2
}
```

Scenario questions additionally carry:

```json
{
  ...
  "scenario_type": "foundation",
  "multiplier_on_excellence": 1.5,
  "typical_duration_rounds": "3-5"
}
```

---

**7. Open Source Scope & Commercial Terms**

**License**: MIT

**Commercial use — MUST contact the author**:
> Commercial use of this project (including but not limited to: selling access to the Agent, bundling in paid products, or using within a commercial service) requires prior written permission from the author. This is a non-negotiable term of the license.
>
> 联系作者获取商业授权: [TODO: email/联系方式]

The intent is to keep the core open for developers while ensuring the author participates in any commercial upside.

**Open source (MIT license)**:
- LangGraph agent logic (`/agent`)
- Follow-up quality gate (`/gate`)
- Question bank format + sample questions (`/questions`)
- Scoring engine (`/scoring`)
- Score report formatter (`/reporting`)

**Not open source** (potential commercial layer):
- Web UI / chat interface
- User authentication + authorization (LeetCode OAuth, etc.)
- Hosted LeetCode problem crawler pipeline
- Subscription / billing layer

---

## 8. Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | Python 3.11+, LangGraph |
| LLM | Anthropic Claude API (claude-3-5-haiku as default, claude-3-7-sonnet as optional) |
| Scoring | Inline LLM call per turn |
| Follow-up gate | Same model, separate evaluation prompt |
| Question storage | Local JSON files (question bank repo) |
| Agent state | LangGraph `MemorySaver` (in-memory) or `SQLiteSaver` (persisted) |
| API layer | FastAPI (optional, for future web UI) |
| Testing | pytest |

---

## 9. Project Structure

```
interview-agent/
├── questions/
│   ├── algorithm/          # crawled, one .json per problem
│   ├── fundamentals/       # crawled, one .json per problem
│   └── scenario/          # self-authored
│       ├── foundation/
│       └── business/
├── agent/
│   ├── __init__.py
│   ├── graph.py            # LangGraph definition
│   ├── state.py            # TypedDict state
│   ├── nodes/
│   │   ├── select_question.py
│   │   ├── ask_question.py
│   │   ├── receive_answer.py
│   │   ├── should_followup.py
│   │   ├── generate_followup.py
│   │   ├── score_answer.py
│   │   ├── advance_pool.py
│   │   └── compile_report.py
│   └── prompts/
│       ├── interviewer_system.txt
│       ├── followup_generator.txt
│       └── gate_evaluator.txt
├── gate/
│   ├── __init__.py
│   └── quality_filter.py   # is_followup_worth_scoring
├── scoring/
│   ├── __init__.py
│   ├── engine.py           # ScoreDelta computation
│   └── dimensions.py       # dimension weight definitions
├── reporting/
│   ├── __init__.py
│   └── formatter.py       # final report structure
├── cli/
│   └── main.py            # candidate-facing CLI
├── tests/
│   ├── test_gate.py
│   ├── test_scoring.py
│   ├── test_followup_loop.py
│   └── fixtures/
│       └── sample_conversation.json
├── pyproject.toml
├── README.md
└── LICENSE (MIT)
```

---

## 10. Resolved & Open Questions

### Resolved
1. **Follow-up loop cap**: 10 total, with early termination support. ✓
2. **Peak bonus magnitude**: +5 per follow-up round. Base scenario score (40) kept separate; this multiplier doesn't dominate. ✓
3. **Gate latency**: Parallel gate+score calls + claude-3-haiku for gate + decision caching. ✓
4. **Question bank seeding**: Two confirmed sources — JavaGuide (javaguide.cn) and 小林coding (xiaolincoding.com). See Question Bank Seeding Sources below. ✓
5. **Scenario question authorship**: Author only for v1. Open contribution in v2. ✓
6. **Gate reliability**: Mitigated via latency controls above. Still needs live testing. See open question #1 below.

### Open Questions (pending first user validation)

1. **Gate reliability at scale**: Does the quality gate produce consistent DV tags across different conversation contexts? Needs A/B testing with live candidates.
2. **Peak bonus calibration**: +5/follow-up — does this create incentive for the AI to ask more trivial follow-ups? Monitor for gate gaming.
3. **Early termination signals**: Are "candidate wants to move on" and "topic fully explored" distinguishable by the AI reliably?
4. **Scenario question volume**: How many self-authored scenario questions are needed before the curiosity-driven loop has enough trigger material? (Target: ~50 minimum for reasonable coverage)