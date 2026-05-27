from scripts.scrape_javaguide import extract_qa_from_html


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