# 面试Agent v1.0：实施计划书

> 目标：跑通最小可行性面试 Agent，验证"好奇心驱动追问 + 峰值评分"核心逻辑。

---

## 阶段概览

| 阶段 | 目标 | 核心交付 |
|------|------|---------|
| Phase 0 | 环境搭建 | 项目骨架 + pyproject.toml |
| Phase 1 | 题库爬取 + 清洗 | questions/ 下有可用 JSON 题库 |
| Phase 2 | 核心 Prompt 验证 | 单轮追问跑通，Prompt 微调 |
| Phase 3 | 追问循环 + Gate | LangGraph 图 + 质量门 |
| Phase 4 | 评分引擎 | 分数计算 + 报告生成 |
| Phase 5 | CLI 界面 | 候选人交互界面 |
| Phase 6 | 完整面试试跑 | 用自己当候选人测一轮 |

---

## Phase 0：环境搭建

**目标**：可运行的项目骨架

### 步骤

1. 创建 `interview-agent/` 目录结构（如 ARCHITECTURE.md 定义）
2. 编写 `pyproject.toml`：
   - 依赖：`langgraph`, `langchain-core`, `anthropic`, `fastapi`（可选）, `pytest`
   - 指定 Python >= 3.11
3. 初始化 Git 仓库，写 `.gitignore`
4. 写 `CLAUDE.md`（项目说明，让 AI 理解项目）
5. 验证：`python -c "from interview_agent import agent"` 不报错

### 验收

- `ls interview-agent/` 目录结构完整
- `pip install -e .` 成功
- `pytest --collect-only` 能收集到测试用例（哪怕0个）

---

## Phase 1：题库爬取 + 清洗

**目标**：fundamentals 题库有可用数据

### 步骤

1. **爬取 JavaGuide 基础面试题**
   - 目标 URL：https://javaguide.cn/java/basis/java-basic-questions-01.html
   - 工具：`requests` + `BeautifulSoup`
   - 爬取范围：标题 + 正文 + 分类标签
   - 输出：临时 Markdown 文件

2. **爬取 小林coding 网络篇**
   - 目标 URL：https://www.xiaolincoding.com/network/
   - 同上

3. **转 JSON 格式**
   - 写一个 `scripts/convert_to_json.py` 转换脚本
   - 遍历 Markdown，每道题转成 `questions/fundamentals/py-foundation-XXX.json`
   - 格式：id / pool / category / difficulty / seed / knowledge_anchors

4. **人工标注场景题**（20道起步）
   - 分类：foundation（多线程/并发/缓存/性能） + business（订单/库存/价格）
   - 每道题含：seed / expected_depth / depth_trigger_pattern / typical_duration_rounds

### 验收

- `questions/fundamentals/` 下有 >= 50 道题 JSON
- `questions/scenario/` 下有 >= 20 道题 JSON
- 每道 JSON 格式校验通过（schema check）

---

## Phase 2：核心 Prompt 验证

**目标**：单轮追问能跑通，AI 追问质量可接受

### 步骤

1. **写 `agent/prompts/interviewer_system.txt`**
   - 系统提示词：定义 AI 面试官角色
   - 核心原则：不暴露数据来源、按峰值定理评分、追问要自然

2. **写 `agent/prompts/followup_generator.txt`**
   - 生成追问内容的 Prompt 模板
   - 输入：当前问题 + 候选人回答 + 历史记录
   - 输出：追问内容 + differentiating_value（HIGH/LOW）

3. **写 `gate/quality_filter.py`**
   - gate 评估 Prompt
   - 判断标准：是否有区分度、是否挖得更深、是否是高频面试题

4. **单轮测试**（在 Python REPL 里手动测）
   - 选一道场景题，给定候选人回答，调用 LLM 生成追问
   - 人工判断：追问是否值得问、是否自然
   - 迭代 Prompt，直到质量达标

### 验收

- 同样的候选人回答，生成的追问稳定（重复调用结果一致或近似）
- 人工评估：>= 80% 的追问"有意义"（不是鸡肋问题）

---

## Phase 3：追问循环 + Gate

**目标**：LangGraph 图完整，追问循环可工作

### 步骤

1. **定义 State**
   ```python
   class InterviewState(TypedDict):
       history: list[Turn]
       current_pool: str
       followup_count: int
       total_followups: int
       scores: list[ScoreDelta]
       candidate_profile: str
   ```

2. **实现 LangGraph 节点**（按 ARCHITECTURE.md Section 4）
   - `select_question` — 从题库选下一题
   - `ask_question` — 渲染题目
   - `receive_answer` — 记录回答
   - `should_followup` — 判断是否继续追问
   - `generate_followup` — 生成追问 + 附 Gate 评估结果
   - `score_answer` — 计算本轮分数
   - `advance_pool` — 切换题库
   - `compile_report` — 生成最终报告

3. **组装 Graph**
   - 边路由：ask → receive → should_followup
   - 条件边：followup_count < 10 → generate_followup，否则 → score_answer
   - 提前终止逻辑写在 `should_followup` 里

4. **集成 Gate**
   - gate 评估和 score_answer **并行执行**（同一个 node 里同时发两个 LLM 调用）
   - Gate 结果写入 state.score

### 验收

- Graph 编译通过，无类型错误
- 手动模拟一轮面试（3题 + 2次追问），状态流转正确
- 总追问数到 10 次时强制结束

---

## Phase 4：评分引擎

**目标**：每轮产生分数，最终出完整报告

### 步骤

1. **实现 `scoring/engine.py`**
   - 接收 `history` + `scores` list
   - 按权重（10/50/40）汇总最终得分
   - 峰值加分：HIGH 追问被接住 +5/轮

2. **实现 `reporting/formatter.py`**
   - 最终报告结构：
     ```json
     {
       "total_score": 72,
       "algorithm_score": 8,
       "fundamentals_score": 38,
       "scenario_score": 26,
       "peak_chains": [{"topic": "concurrency", "rounds": 3, "peak_bonus": 15}],
       "weak_points": ["TCP滑动窗口概念模糊"],
       "strong_points": ["JVM内存模型讲得很透"]
     }
     ```

3. **集成进 Graph**
   - `compile_report` node 调用 formatter
   - 面试结束时输出结构化报告

### 验收

- 模拟数据跑一遍，报告结构正确
- 峰值加分计算正确
- 各维度分数加起来 = 100

---

## Phase 5：CLI 界面

**目标**：候选人可通过命令行开始面试

### 步骤

1. **实现 `cli/main.py`**
   - 命令：`interview-agent start --profile java-backend`
   - 交互：显示题目 → 读取候选人输入 → 传给 Graph → 显示结果 → 循环
   - 显示：每题显示 + 每轮追问 + 每轮分数

2. **实现 `interview-agent` 命令**
   - `pyproject.toml` 里定义 console_scripts 入口点
   - 安装后可直接运行 `interview-agent`

3. **候选人设置**
   - 可输入 profile（岗位描述）让 AI 调整难度
   - 可跳过当前题（算答不好）

### 验收

- 运行 `interview-agent start`，交互正常
- Ctrl+C 能优雅退出
- 面试结束自动输出报告

---

## Phase 6：完整面试试跑

**目标**：用自己当候选人跑完整流程，发现实际问题

### 步骤

1. **准备阶段**
   - 确认题库 >= 50 fundamentals + >= 20 scenario
   - 确认 CLI 可正常运行

2. **正式试跑**（作者自己做候选人）
   - 从算法题开始（10%权重）
   - 八股文随机抽题（50%权重）
   - 场景题触发追问链（40%权重）
   - 记录：哪道题 AI 追问得好、哪道题 AI 追问得奇怪

3. **问题修复**
   - 根据试跑结果调整 Prompt
   - 根据试跑结果调整评分参数（+5/轮是否合适）
   - 根据试跑结果补充场景题（补到 >= 50）

4. **写测试用例**
   - `tests/test_followup_loop.py`：固定 conversation history，验证追问数量
   - `tests/test_gate.py`：固定 followup，验证 gate 评分一致性
   - `tests/test_scoring.py`：模拟数据，验证总分计算

### 验收

- 完整跑完一轮，分数合理
- 追问链有峰值加分体验
- pytest 通过

---

## 里程碑时间线（预估）

| 阶段 | 预估工时 | 累计 |
|------|---------|------|
| Phase 0 | 1-2h | 1-2h |
| Phase 1 | 4-6h | 5-8h |
| Phase 2 | 3-4h | 8-12h |
| Phase 3 | 4-6h | 12-18h |
| Phase 4 | 2-3h | 14-21h |
| Phase 5 | 2-3h | 16-24h |
| Phase 6 | 2-4h | 18-28h |

**总预估：18-28 小时（分 4-6 天做完）**

---

## 风险 & 应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| Gate 延迟严重 | 中 | 高 | 并行调用 + haiku model |
| 追问质量不稳定 | 高 | 高 | Phase 2 充分 Prompt 迭代 |
| 题库爬取被反爬 | 低 | 中 | 用 requests +UA轮换 |
| LangGraph 状态流转 bug | 中 | 中 | Phase 3 单元测试覆盖 |
| 评分不符合直觉 | 中 | 高 | Phase 6 真人试跑必做 |

---

*Last updated: 2026-05-26*
*Author: [TODO: 补充联系方式]*