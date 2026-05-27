# Phase 1 实现文档：题库爬取 + 清洗

> 本文档定义 Phase 1 的完整实现细节。实现前请阅读完毕，代码须遵循「TDD」流程：先写测试，再写业务代码。

---

## 交付目标

```
questions/
  algorithm/          # 算法题（10%权重），暂不爬，手动标注
    *.json
  fundamentals/       # 八股文题（50%权重）
    py-foundation-*.json   # Python 基础
    jvm-*.json             # JVM
    concurrency-*.json     # 并发
    network-*.json         # 计算机网络
    mysql-*.json           # MySQL
  scenario/           # 场景题（40%权重），手动标注
    foundation/*.json
    business/*.json
```

验收标准：
- `questions/fundamentals/` 下有 >= 50 道题 JSON
- `questions/scenario/` 下有 >= 20 道题 JSON
- 每道 JSON 格式校验通过（schema check）

---

## 1. 项目依赖补充

**文件：** `pyproject.toml`

在现有 `[project.dependencies]` 中追加：

```toml
requests = "^2.32.0"
beautifulsoup4 = "^4.12.0"
lxml = "^5.2.0"
html2text = "^2024.2.0"
```

验证：
```bash
source .venv/bin/activate
pip install -e .
pip install requests beautifulsoup4 lxml html2text
```

---

## 2. 题库 JSON Schema

**文件：** `questions/schema.py`

每道题的 JSON 必须符合以下 schema：

```python
from typing import Literal

class Question(TypedDict, total=False):
    id: str                          # 唯一标识，例："py-foundation-001"
    pool: Literal["algorithm", "fundamentals", "scenario"]
    category: str                    # 子类，例："async", "jvm", "concurrency"
    difficulty: Literal["easy", "medium", "hard"]
    seed: str                        # 种子问题，完整的面试题正文
    knowledge_anchors: list[str]     # 知识点列表，用于评分引擎关联
    # 以下字段仅 scenario 题库有
    depth_trigger_pattern: str | None # 触发追问的关键词模式
    expected_depth: int | None       # 期望追问层数
    typical_duration_rounds: int | None  # 典型追问轮数
```

**测试文件：** `tests/test_schema.py`

```python
# tests/test_schema.py
import json
from pathlib import Path

SCHEMA_KEYS = {"id", "pool", "category", "difficulty", "seed", "knowledge_anchors"}

def test_all_question_files_are_valid_json():
    """questions/ 下所有 .json 文件格式合法"""
    questions_dir = Path(__file__).parent.parent / "questions"
    for pool_dir in questions_dir.iterdir():
        if not pool_dir.is_dir():
            continue
        for json_file in pool_dir.rglob("*.json"):
            with open(json_file) as f:
                data = json.load(f)
            missing = SCHEMA_KEYS - set(data.keys())
            assert not missing, f"{json_file} missing keys: {missing}"

def test_question_ids_are_unique():
    """所有 question id 全局唯一"""
    questions_dir = Path(__file__).parent.parent / "questions"
    ids = []
    for pool_dir in questions_dir.iterdir():
        if not pool_dir.is_dir():
            continue
        for json_file in pool_dir.rglob("*.json"):
            with open(json_file) as f:
                data = json.load(f)
            ids.append(data["id"])
    assert len(ids) == len(set(ids)), f"duplicate ids: {set([x for x in ids if ids.count(x)>1])}"
```

---

## 3. 爬取脚本：JavaGuide 基础面试题

**文件：** `scripts/scrape_javaguide.py`

### 3.1 设计

- 用 `requests.Session()` 保持连接，UA 轮换防止被ban
- 每个 Topic 一个 JSON 文件，按 `category` 分类
- `knowledge_anchors` 从标题和正文关键词提取

### 3.2 实现步骤

```
scripts/scrape_javaguide.py
├── ScrapeConfig（配置类）
│   └── BASE_URL = "https://javaguide.cn"
│   └── HEADERS 轮换池（5个UA）
│   └── DELAY    = 1.5  # 请求间隔秒数
│
├── fetch_page(url: str) → str
│   └── Session带重试（max 3次）
│   └── 返回页面HTML或raise
│
├── parse_javaguide_topics(html: str) → list[dict]
│   └── BeautifulSoup解析左侧导航栏
│   └── 提取：topic名称 / relative_url / category标签
│   └── 分类映射：
│       Java基础 → py-foundation（复用格式，仅改内容）
│       JVM → jvm
│       并发 → concurrency
│       MySQL → mysql
│       计算机网络 → network
│
├── parse_topic_page(html: str, topic: str) → list[dict]
│   └── 解析正文：题目在 <h2>/<h3> 或 Q&A 块里
│   └── 每道题提取：question_text / answer_text（可选）
│   └── 题目难度默认 medium（无原始难度标记）
│   └── knowledge_anchors = [topic] + 从正文中提取的关键词
│
├── save_questions(questions: list[dict], category: str)
│   └── 写入 questions/fundamentals/{category}-001.json 等
│   └── 每文件最多50题（超出则分文件）
│
└── main()
    └── 遍历所有topic，串行请求 → 解析 → 保存
```

### 3.3 关键代码片段

```python
# fetch_page
def fetch_page(session: requests.Session, url: str) -> str:
    for attempt in range(3):
        try:
            resp = session.get(url, timeout=10)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")

# parse_topic_page — 题目识别正则
QUESTION_HEADERS = re.compile(r'^(#{1,3})\s*([^\n]+?)(?:\n|$)', re.MULTILINE)
# 题目通常以 ## 开头，或在 <li>/<p> 中以问号结尾
CANDIDATE_QUESTION = re.compile(r'([^\n。！？]+[？?])\s*$', re.UNICODE)
```

### 3.4 测试

```python
# tests/test_scrape_javaguide.py
from scripts.scrape_javaguide import fetch_page, parse_javaguide_topics
from unittest.mock import patch, MagicMock

def test_fetch_page_success():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html><body>test</body></html>"
    with patch("requests.Session") as MockSession:
        instance = MockSession.return_value
        instance.get.return_value = mock_resp
        html = fetch_page(instance, "https://example.com")
        assert "test" in html

def test_parse_topics_extracts_navigation():
    html = """
    <html><body>
    <nav><a href="/java/basis/java-basic-questions-01.html">Java基础</a></nav>
    </body></html>
    """
    topics = parse_javaguide_topics(html)
    assert len(topics) >= 1
    assert any("Java基础" in t["name"] for t in topics)
```

---

## 4. 爬取脚本：小林coding 网络篇

**文件：** `scripts/scrape_xiaolincoding.py`

### 4.1 设计

- 小林coding 网站结构与 JavaGuide 类似
- 目标 URL：`https://www.xiaolincoding.com/network/`
- 左侧导航抓网络分类页面
- 网络协议层分类：TCP/UDP、HTTP、HTTPS、Socket、协议基础

### 4.2 实现步骤

```
scripts/scrape_xiaolincoding.py
├── BASE_URL = "https://www.xiaolincoding.com"
├── parse_network_topics(html: str) → list[dict]
│   └── 导航解析同 JavaGuide
│   └── 分类：tcp-udp / http / https / socket / protocol
│
├── parse_network_page(html: str, topic: str) → list[dict]
│   └── 题目识别同上
│   └── knowledge_anchors = [topic] + 协议关键词
│
└── main()
```

### 4.3 测试桩

同上，用 `unittest.mock` mock `requests.Session`

---

## 5. 转换脚本：Markdown → JSON

**文件：** `scripts/convert_to_json.py`

如果爬取阶段输出中间 Markdown 文件（而非直接写 JSON），则用此脚本转换。

### 5.1 设计

```python
# 输入：questions/fundamentals/raw/*.md
# 输出：questions/fundamentals/{category}-{NNN}.json

def convert_file(md_path: Path, output_dir: Path, category: str):
    content = md_path.read_text(encoding="utf-8")
    questions = extract_qa_blocks(content)  # 解析MD中的Q&A块
    for i, q in enumerate(questions, start=1):
        obj = {
            "id": f"{category}-{i:03d}",
            "pool": "fundamentals",
            "category": category,
            "difficulty": q.get("difficulty", "medium"),
            "seed": q["question"],
            "knowledge_anchors": q.get("anchors", [category]),
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        out_path = output_dir / f"{category}-{i:03d}.json"
        out_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2))
```

### 5.2 测试

```python
# tests/test_convert.py
from scripts.convert_to_json import extract_qa_blocks

def test_extract_qa_blocks():
    md = """
## 1. 什么是 Java 虚拟机（JVM）？

JVM 是 Java Virtual Machine 的缩写，是一种虚拟计算机...

## 2. JVM 的主要组成部分有哪些？

JVM 主要包含：类加载器、运行时数据区、执行引擎...
    """
    blocks = extract_qa_blocks(md)
    assert len(blocks) == 2
    assert "JVM" in blocks[0]["question"]
    assert "主要组成" in blocks[1]["question"]
```

---

## 6. 场景题人工标注指南

**文件：** `questions/SCENARIO_ANNOTATION_GUIDE.md`

手动标注 20 道起步，分两类：

### 6.1 foundation（多线程/并发/缓存/性能）

格式示例：

```json
{
  "id": "scenario-foundation-001",
  "pool": "scenario",
  "category": "concurrency",
  "difficulty": "hard",
  "seed": "如果让你设计一个每秒处理10万下单的秒杀系统，你会怎么设计库存扣减流程？如何避免超卖？",
  "knowledge_anchors": ["乐观锁", "Redis原子操作", "消息队列", "限流"],
  "depth_trigger_pattern": "候选人提到'乐观锁'或'Redis'后，追问其实践细节",
  "expected_depth": 3,
  "typical_duration_rounds": 4
}
```

### 6.2 business（订单/库存/价格）

格式示例：

```json
{
  "id": "scenario-business-001",
  "pool": "scenario",
  "category": "order",
  "difficulty": "medium",
  "seed": "美团外卖订单系统需要支持提前点单（用户提前一周下单，商家当天制作）。你会如何设计订单的状态机？请列出所有状态及触发条件。",
  "knowledge_anchors": ["状态机", "幂等", "超时取消", "分布式事务"],
  "depth_trigger_pattern": "候选人提到'状态机'后追问各状态转换边界条件",
  "expected_depth": 2,
  "typical_duration_rounds": 3
}
```

---

## 7. TDD 开发顺序

```
Step 1: 写 tests/test_schema.py  ← 先写schema验证测试
Step 2: 实现 questions/schema.py  ← 让Step 1通过
Step 3: 写 tests/test_scrape_javaguide.py  ← 爬虫测试桩
Step 4: 实现 scripts/scrape_javaguide.py  ← 让Step 3通过
Step 5: 写 tests/test_scrape_xiaolincoding.py
Step 6: 实现 scripts/scrape_xiaolincoding.py
Step 7: 写 tests/test_convert.py
Step 8: 实现 scripts/convert_to_json.py
Step 9: 手动标注 scenario 场景题 >= 20道
Step 10: 全量运行 tests/test_schema.py 验证题库
```

---

## 8. 运行命令汇总

```bash
# 安装依赖
source ~/interview-agent/.venv/bin/activate
pip install requests beautifulsoup4 lxml html2text

# 爬取 JavaGuide
python -m scripts.scrape_javaguide

# 爬取 小林coding
python -m scripts.scrape_xiaolincoding

# 转换中间文件
python -m scripts.convert_to_json

# 验证题库
pytest tests/test_schema.py -v

# 全量测试
pytest -v
```

---

*本文档为 Phase 1 实现细节。Phase 2 Prompt 验证依赖本题库，请先完成本题库再进入 Phase 2。*