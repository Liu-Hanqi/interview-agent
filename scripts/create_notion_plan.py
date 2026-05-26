#!/usr/bin/env python3
"""Create Implementation Plan page in Notion."""
import urllib.request
import json
import os

API_KEY = os.environ.get('NOTION_API_KEY', '')
HEADERS = {
    'Authorization': f'Bearer {API_KEY}',
    'Notion-Version': '2025-09-03',
    'Content-Type': 'application/json'
}

def create_page(parent_id, title, children):
    payload = {
        'parent': {'page_id': parent_id},
        'properties': {
            'title': [{'text': {'content': title}}]
        },
        'children': children
    }
    req = urllib.request.Request(
        'https://api.notion.com/v1/pages',
        data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
        headers=HEADERS,
        method='POST'
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def h1(text):
    return {'object': 'block', 'type': 'heading_1', 'heading_1': {'rich_text': [{'text': {'content': text}}]}}

def h2(text):
    return {'object': 'block', 'type': 'heading_2', 'heading_2': {'rich_text': [{'text': {'content': text}}]}}

def h3(text):
    return {'object': 'block', 'type': 'heading_3', 'heading_3': {'rich_text': [{'text': {'content': text}}]}}

def para(text):
    return {'object': 'block', 'type': 'paragraph', 'paragraph': {'rich_text': [{'text': {'content': text}}]}}

def bullet(text):
    return {'object': 'block', 'type': 'bulleted_list_item', 'bulleted_list_item': {'rich_text': [{'text': {'content': text}}]}}

def divider():
    return {'object': 'block', 'type': 'divider', 'divider': {}}

PARENT = '36c23164-6e6b-8195-8309-de7543622e95'  # product doc page

children = [
    h1('阶段概览'),
    para('目标：跑通最小可行性面试 Agent，验证"好奇心驱动追问 + 峰值评分"核心逻辑'),

    h2('Phase 0 — 环境搭建（1-2h）'),
    bullet('创建 interview-agent/ 目录结构'),
    bullet('pyproject.toml：langgraph / langchain-core / anthropic / pytest'),
    bullet('Python >= 3.11'),
    bullet('初始化 Git 仓库'),
    bullet('验收：pip install -e . 成功；pytest --collect-only 能收集测试'),

    h2('Phase 1 — 题库爬取 + 清洗（4-6h）'),
    bullet('爬取 JavaGuide 基础面试题 → Markdown'),
    bullet('爬取 小林coding 网络篇 → Markdown'),
    bullet('scripts/convert_to_json.py：Markdown → questions/fundamentals/*.json（>=50道）'),
    bullet('人工标注场景题 20 道（foundation/business 各半）'),
    bullet('验收：题库 >= 70 道 JSON，格式校验通过'),

    h2('Phase 2 — 核心 Prompt 验证（3-4h）'),
    bullet('agent/prompts/interviewer_system.txt — AI 面试官系统提示词'),
    bullet('agent/prompts/followup_generator.txt — 生成追问内容 + differentiating_value'),
    bullet('gate/quality_filter.py — Gate 评估 Prompt（是否有区分度）'),
    bullet('单轮人工测试：固定候选人回答，调用 LLM 生成追问，评估质量'),
    bullet('验收：>=80% 追问"有意义"，重复调用结果稳定'),

    h2('Phase 3 — 追问循环 + Gate（4-6h）'),
    bullet('定义 InterviewState（TypedDict）：history / current_pool / followup_count / total_followups / scores / candidate_profile'),
    bullet('实现 LangGraph 节点：select_question / ask_question / receive_answer / should_followup / generate_followup / score_answer / advance_pool / compile_report'),
    bullet('组装 Graph：边路由 + 条件边（followup_count < 10）+ 提前终止逻辑'),
    bullet('集成 Gate：评分 + gate 并行执行（同一 node 两个 LLM 调用）'),
    bullet('验收：Graph 编译通过；模拟 3 题 + 2 次追问状态流转正确；追问数到 10 强制结束'),

    h2('Phase 4 — 评分引擎（2-3h）'),
    bullet('scoring/engine.py：按权重汇总分数 + 峰值加分计算'),
    bullet('reporting/formatter.py：最终报告 JSON（total_score / 算法分 / 八股分 / 场景分 / peak_chains / weak_points / strong_points）'),
    bullet('集成进 compile_report node'),
    bullet('验收：模拟数据跑一遍，报告结构正确，各维度相加 = 100'),

    h2('Phase 5 — CLI 界面（2-3h）'),
    bullet('cli/main.py：interview-agent start --profile <岗位描述>'),
    bullet('pyproject.toml 定义 console_scripts 入口点'),
    bullet('交互：显示题目 → 读取输入 → 传给 Graph → 显示分数 → 循环'),
    bullet('候选人可跳过当前题（算答不好）'),
    bullet('验收：Ctrl+C 优雅退出；面试结束自动输出报告'),

    h2('Phase 6 — 完整面试试跑（2-4h）'),
    bullet('作者自己做候选人，完整跑完算法/八股/场景三轮'),
    bullet('问题修复：根据试跑调整 Prompt 和评分参数'),
    bullet('补充场景题到 >= 50 道'),
    bullet('写测试用例：test_followup_loop / test_gate / test_scoring'),
    bullet('验收：pytest 通过；完整跑完分数合理；有峰值加分体验'),

    divider(),

    h1('里程碑时间线（预估）'),
    bullet('Phase 0：1-2h → 累计 1-2h'),
    bullet('Phase 1：4-6h → 累计 5-8h'),
    bullet('Phase 2：3-4h → 累计 8-12h'),
    bullet('Phase 3：4-6h → 累计 12-18h'),
    bullet('Phase 4：2-3h → 累计 14-21h'),
    bullet('Phase 5：2-3h → 累计 16-24h'),
    bullet('Phase 6：2-4h → 累计 18-28h'),
    para('总预估：18-28 小时，分 4-6 天做完'),

    divider(),

    h1('风险 & 应对'),
    bullet('Gate 延迟严重 — 应对：并行调用 + haiku model'),
    bullet('追问质量不稳定 — 应对：Phase 2 充分 Prompt 迭代'),
    bullet('题库爬取被反爬 — 应对：requests + UA 轮换'),
    bullet('LangGraph 状态流转 bug — 应对：Phase 3 单元测试覆盖'),
    bullet('评分不符合直觉 — 应对：Phase 6 真人试跑必做'),
]

result = create_page(PARENT, '面试Agent v1.0：实施计划书', children)
print('Created page ID:', result.get('id'))