#!/usr/bin/env python3
"""Create Interview Agent product doc in Notion."""
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
    return {
        'object': 'block', 'type': 'heading_1',
        'heading_1': {'rich_text': [{'text': {'content': text}}]}
    }

def h2(text):
    return {
        'object': 'block', 'type': 'heading_2',
        'heading_2': {'rich_text': [{'text': {'content': text}}]}
    }

def para(*parts):
    rich_text = []
    for p in parts:
        if isinstance(p, str):
            rich_text.append({'text': {'content': p}})
        else:
            rich_text.append(p)
    return {'object': 'block', 'type': 'paragraph', 'paragraph': {'rich_text': rich_text}}

def bullet(*parts):
    rich_text = []
    for p in parts:
        if isinstance(p, str):
            rich_text.append({'text': {'content': p}})
        else:
            rich_text.append(p)
    return {'object': 'block', 'type': 'bulleted_list_item', 'bulleted_list_item': {'rich_text': rich_text}}

children = [
    h1('产品定位'),
    para('AI 面试官，开源核心推理引擎，商业化用户体验层。Python 方向，LangGraph + 自定义评分引擎。第一个目标用户：作者本人。'),

    h1('题库结构（三个独立模块）'),
    para('Algorithm 算法题库 · 10% · AI 随机抽题，候选人不暴露刷题记录 · 允许口述思路，按思路完整性给部分分'),
    para('Fundamentals 八股文库 · 50% · 随机抽题 · 流畅度加分；答不好扣分'),
    para('Scenario 场景题库 · 40% · 好奇心驱动，没有固定题目 · 追问链触发峰值加分'),

    h2('场景题分类（两级）'),
    bullet('Foundation — 多线程、并发、异步、缓存、消息队列、分布式系统、性能'),
    bullet('Business — 预订流程、库存管理、供应商集成、价格计算、订单状态机'),

    h1('核心追问机制'),
    para('流程：回答 → AI 判断感兴趣点 → 追问A → 接住 → 追问A\' → 接住 → 能接住2轮以上 = 上限触到，结束此话题'),
    para('追问循环：最高 10 次，可提前终止（接不住 / 话题已充分探索 / 候选人主动跳过）'),
    para('连续追问本身 = 考核设计思维 + 八股功底的复合能力'),

    h1('评分体系（峰值定理）'),
    bullet('八股答好 = +小分；答不好 = 扣分'),
    bullet('算法口述思路 = 按质量给部分分'),
    bullet('场景题峰值：AI 好奇 + 候选人接住 = 大幅加分'),
    bullet('Gate 评估并行执行防延迟；Gate 用 haiku，生成用 sonnet'),

    h1('一致性约束'),
    bullet('AI 追问的价值由区分度决定（只有一定经验才能接住的问题才值得问）'),
    bullet('不暴露候选人刷题记录；AI 出题完全独立随机'),
    bullet('Gate 评估：高分追问才触发峰值加分，低分追问答好也不加分'),

    h1('最终得分构成'),
    bullet('算法（10%）— 最高 10 分'),
    bullet('八股文（50%）— 最高 50 分'),
    bullet('场景题（40%）— 最高 40 分'),
    bullet('合计 100 分'),

    h1('题库数据源'),
    bullet('JavaGuide (javaguide.cn) — 八股文'),
    bullet('小林coding (xiaolincoding.com) — 网络基础 / 场景题'),

    h1('开源条款'),
    para('协议：MIT；商用必须联系作者获取授权；商用定义：出售访问权限、捆绑付费产品、商业服务内使用'),
]

# Parent page: hermes工作空间
PARENT = '35923164-6e6b-806d-81e4-f960b10f4aeb'

result = create_page(PARENT, '面试Agent v1.0：产品需求文档', children)
print('Created page ID:', result.get('id'))
print('URL: https://notion.so/', result.get('id', '').replace('-', ''))