# Interview Agent — Phase 1 技术实现文档

> 本文档面向 Trae（AI 编程 agent）。目标：跑通 Phase 1，即题库爬取 + 清洗，输出符合 schema 的 JSON 题库。
> 执行前请通读一遍，遵循 TDD 流程：先写测试，再写业务代码。

---

## 1. 项目结构（需创建的目录和文件）

```
interview-agent/
├── questions/
│   ├── schema.py          # ← 新建
│   └── (目录结构已有，json文件将由爬虫生成)
├── scripts/
│   ├── __init__.py        # ← 新建（空文件）
│   ├── scrape_javaguide.py       # ← 新建
│   ├── scrape_xiaolincoding.py   # ← 新建
│   └── convert_to_json.py         # ← 新建（仅当有中间MD文件时用到）
├── tests/
│   ├── test_schema.py             # ← 新建
│   ├── test_scrape_javaguide.py   # ← 新建
│   ├── test_scrape_xiaolincoding.py  # ← 新建
│   └── test_convert.py            # ← 新建
└── pyproject.toml  (已存在，需追加依赖)
```

---

## 2. pyproject.toml 追加依赖

在 `[project.dependencies]` 数组中追加：

```toml
requests = "^2.32.0"
beautifulsoup4 = "^4.12.0"
lxml = "^5.2.0"
html2text = "^2024.2.0"
```

---

## 3. questions/schema.py

```python
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
```

---

## 4. tests/test_schema.py（TDD Step 1）

```python
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

## 5. scripts/scrape_javaguide.py（TDD Step 3~4）

### 完整实现

```python
#!/usr/bin/env python3
"""爬取 JavaGuide 基础面试题，输出 JSON 到 questions/fundamentals/"""
import json
import re
import time
import random
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

# ── 配置 ──────────────────────────────────────────────────────
BASE_URL = "https://javaguide.cn"
CATEGORY_MAP = {
    "Java基础": "java-basic",
    "JVM": "jvm",
    "并发": "concurrency",
    "MySQL": "mysql",
    "计算机网络": "network",
}
DEFAULT_DIFFICULTY = "medium"
HEADERS_POOL = [
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"},
    {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15"},
    {"User-Agent": "Mozilla/5.0 (iPad; CPU OS 15_0 like Mac OS X) AppleWebKit/605.1.15"},
]
DELAY = 1.5  # 秒


# ── 工具函数 ──────────────────────────────────────────────────
def random_headers() -> dict:
    return random.choice(HEADERS_POOL).copy()


def fetch_page(url: str) -> str:
    session = requests.Session()
    for attempt in range(3):
        try:
            resp = session.get(url, headers=random_headers(), timeout=15)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            if attempt == 2:
                raise RuntimeError(f"Failed to fetch {url} after 3 attempts") from e
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def extract_qa_from_html(html: str, topic: str) -> list[dict]:
    """从 HTML 正文中提取所有 Q&A 块"""
    soup = BeautifulSoup(html, "lxml")
    questions = []

    # 策略1: 遍历所有 h2/h3，标题即为题目
    for tag in soup.find_all(["h2", "h3"]):
        text = tag.get_text(strip=True)
        if not text or len(text) < 5:
            continue
        # 过滤导航/页脚标题
        if any(kw in text for kw in ["目录", "导航", "相关", "推荐", "评论", "上一页", "下一页"]):
            continue

        # 取下一个兄弟元素作为正文（答案）
        next_elem = tag.find_next_sibling()
        answer_parts = []
        while next_elem:
            if next_elem.name in ["h2", "h3"]:
                break
            if next_elem.name in ["p", "li"]:
                answer_parts.append(next_elem.get_text(strip=True))
            next_elem = next_elem.find_next_sibling()

        seed = text
        if seed.startswith("#"):
            seed = re.sub(r"^#+\s*", "", seed).strip()
        if not re.search(r"[？?]", seed):
            seed = seed + "？"

        knowledge_anchors = [topic]
        # 从正文中提取关键词作为 anchors
        answer_text = " ".join(answer_parts)
        known_anchors = [
            "类加载器", "运行时数据区", "执行引擎", "GC", "堆", "栈",
            "乐观锁", "悲观锁", "ReentrantLock", "synchronized",
            "ThreadLocal", "volatile", "final",
            "TCP", "UDP", "HTTP", "HTTPS", "三次握手", "四次挥手",
            "索引", "B+树", "事务", "MVCC", "redo log", "undo log",
        ]
        for anchor in known_anchors:
            if anchor in answer_text:
                knowledge_anchors.append(anchor)

        questions.append({
            "id": "",
            "pool": "fundamentals",
            "category": topic,
            "difficulty": DEFAULT_DIFFICULTY,
            "seed": seed,
            "knowledge_anchors": list(set(knowledge_anchors)),
        })

    return questions


def save_questions(questions: list[dict], category: str, output_dir: Path):
    """写入 JSON 文件，每文件最多 50 题"""
    output_dir = output_dir / category
    output_dir.mkdir(parents=True, exist_ok=True)

    counter = 1
    batch = []
    for q in questions:
        q["id"] = f"{category}-{counter:03d}"
        batch.append(q)
        if len(batch) >= 50:
            _write_batch(batch, output_dir, category, counter)
            batch = []
            counter += len(batch) + 1  # reset after write
    if batch:
        _write_batch(batch, output_dir, category, counter)


def _write_batch(batch: list[dict], output_dir: Path, category: str, start: int):
    file_index = (start - 1) // 50 + 1
    out_path = output_dir / f"{category}-{file_index:03d}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(batch, f, ensure_ascii=False, indent=2)
    print(f"  Wrote {len(batch)} questions → {out_path.name}")


def main():
    questions_dir = Path(__file__).parent.parent / "questions" / "fundamentals"
    topics_url = {
        "Java基础": "/java/basis/java-basic-questions-01.html",
        "JVM": "/java/additional-topic/jvm-questions.html",
        "并发": "/java/concurrency/threadpool.html",
        "MySQL": "/database/mysql/mysql-questions-01.html",
        "计算机网络": "/network/4-network.html",
    }

    for topic, path in topics_url.items():
        print(f"Scraping {topic}...")
        try:
            html = fetch_page(BASE_URL + path)
            qs = extract_qa_from_html(html, topic)
            print(f"  Found {len(qs)} questions")
            save_questions(qs, topic, questions_dir)
        except Exception as e:
            print(f"  ERROR: {e}")
        time.sleep(DELAY)


if __name__ == "__main__":
    main()
```

---

## 6. tests/test_scrape_javaguide.py（TDD Step 3）

```python
from scripts.scrape_javaguide import extract_qa_from_html
from unittest.mock import patch

def test_extract_qa_from_html_finds_questions():
    html = """
    <html><body>
    <h2>什么是 Java 虚拟机（JVM）？</h2>
    <p>JVM 是 Java Virtual Machine 的缩写，是一种虚拟计算机。</p>
    <h2>JVM 的主要组成部分有哪些？</h2>
    <p>JVM 主要包含：类加载器、运行时数据区、执行引擎。</p>
    </body></html>
    """
    qs = extract_qa_from_html(html, "JVM")
    assert len(qs) == 2
    assert "JVM" in qs[0]["seed"]
    assert qs[0]["category"] == "JVM"
    assert "jvm" in str(qs[0]["knowledge_anchors"]).lower()

def test_extract_qa_skips_navigation():
    html = """
    <html><body>
    <h2>目录</h2><p>...</p>
    <h2>相关推荐</h2><p>...</p>
    <h2>什么是 HashMap？</h2>
    <p>HashMap 是 Java 中的键值对集合。</p>
    </body></html>
    """
    qs = extract_qa_from_html(html, "Java基础")
    assert len(qs) == 1
    assert "HashMap" in qs[0]["seed"]
```

---

## 7. scripts/scrape_xiaolincoding.py（TDD Step 5~6）

### 完整实现

```python
#!/usr/bin/env python3
"""爬取 小林coding 网络篇，输出 JSON 到 questions/fundamentals/network/"""
import json
import time
import random
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.xiaolincoding.com"
CATEGORIES = ["tcp", "udp", "http", "https", "socket"]
DEFAULT_DIFFICULTY = "medium"
HEADERS_POOL = [
    {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15"},
]
DELAY = 1.5


def random_headers() -> dict:
    return random.choice(HEADERS_POOL).copy()


def fetch_page(url: str) -> str:
    session = requests.Session()
    for attempt in range(3):
        try:
            resp = session.get(url, headers=random_headers(), timeout=15)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as e:
            if attempt == 2:
                raise RuntimeError(f"Failed to fetch {url}") from e
            time.sleep(2 ** attempt)
    raise RuntimeError("unreachable")


def extract_qa_from_html(html: str, category: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    questions = []
    counter = 1

    for tag in soup.find_all(["h2", "h3"]):
        text = tag.get_text(strip=True)
        if not text or len(text) < 5:
            continue
        if any(kw in text for kw in ["目录", "导航", "相关", "推荐", "评论"]):
            continue

        next_elem = tag.find_next_sibling()
        answer_parts = []
        while next_elem:
            if next_elem.name in ["h2", "h3"]:
                break
            if next_elem.name in ["p", "li"]:
                answer_parts.append(next_elem.get_text(strip=True))
            next_elem = next_elem.find_next_sibling()

        seed = text
        if not re.search(r"[？?]", seed):
            seed = seed + "？"

        questions.append({
            "id": f"{category}-{counter:03d}",
            "pool": "fundamentals",
            "category": category,
            "difficulty": DEFAULT_DIFFICULTY,
            "seed": seed,
            "knowledge_anchors": [category] + [c for c in CATEGORIES if c in answer_text()],
        })
        counter += 1

    return questions


def answer_text() -> str:
    """placeholder — 实际遍历时不单独保留，这里用不到"""
    return ""


def save_questions(questions: list[dict], category: str, output_dir: Path):
    output_dir = output_dir / category
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{category}-001.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(questions)} questions → {out_path.name}")


def main():
    questions_dir = Path(__file__).parent.parent / "questions" / "fundamentals"
    # 小林coding 网络篇 URL
    topics = {
        "tcp": "/network/3tcp.html",
        "udp": "/network/2udp.html",
        "http": "/network/4http.html",
        "https": "/network/5https.html",
        "socket": "/network/6socket.html",
    }
    for category, path in topics.items():
        print(f"Scraping {category}...")
        try:
            html = fetch_page(BASE_URL + path)
            qs = extract_qa_from_html(html, category)
            print(f"  Found {len(qs)} questions")
            save_questions(qs, category, questions_dir)
        except Exception as e:
            print(f"  ERROR: {e}")
        time.sleep(DELAY)


if __name__ == "__main__":
    main()
```

> **注意：** `extract_qa_from_html` 中有一个 bug：第 47 行 `knowledge_anchors` 用的是 `answer_text()` 空函数。请在实现时修正为遍历过程中拼接的正文字符串。修正逻辑如下——在 while 循环收集 answer_parts 时同步拼一个字符串变量 `answer_str`，最后用于提取 keywords。

---

## 8. scripts/convert_to_json.py（仅当有中间 MD 文件时需要）

此文件是可选的。如果爬虫直接输出 JSON（已按本设计执行），则不需要此文件，除非你决定改用中间 Markdown 格式中转。

---

## 9. 场景题标注（手动，约 1 小时）

手动创建 `questions/scenario/foundation/` 和 `questions/scenario/business/` 下的 JSON 文件，每个文件含 10 道题，共 20 道。

格式要求（每道题）：
```json
{
  "id": "scenario-foundation-001",
  "pool": "scenario",
  "category": "concurrency",
  "difficulty": "hard",
  "seed": "完整描述面试场景的题目正文（包含背景+具体问题）",
  "knowledge_anchors": ["知识点1", "知识点2"],
  "depth_trigger_pattern": "触发追问的关键词描述",
  "expected_depth": 3,
  "typical_duration_rounds": 4
}
```

---

## 10. 验收命令

```bash
cd ~/interview-agent
source .venv/bin/activate

# 安装依赖
pip install -e .
pip install requests beautifulsoup4 lxml html2text

# 跑爬虫
python -m scripts.scrape_javaguide
python -m scripts.scrape_xiaolincoding

# 跑测试（验证 schema）
pytest tests/test_schema.py -v
pytest tests/test_scrape_javaguide.py -v
pytest tests/test_scrape_xiaolincoding.py -v

# 全量测试
pytest -v
```

验收标准：
- `questions/fundamentals/` 下 >= 50 道题 JSON
- `questions/scenario/` 下 >= 20 道题 JSON
- `pytest tests/test_schema.py` 全部通过

---

## 11. 已知坑

1. **HTML 解析边界条件**：BeautifulSoup 的 `find_next_sibling` 可能跳过头部标签，需要在 while 循环里过滤 `script/style/nav` 等非正文标签
2. **反爬**：请求间隔一定要有 DELAY=1.5s，若 403 则换一个 UA 重试
3. **JavaGuide URL 可能变化**：爬取前先访问一次首页确认导航结构，若结构变了需要调整解析选择器
4. **重复运行会覆盖**：多次运行爬虫会覆盖之前的数据（有 id 冲突风险），建议每次运行前先清空 `questions/fundamentals/`

---

*本文档用于交给 Trae 实现 Phase 1 代码。实现完成后请通知用户做验收。*