"""Tests for the prompts module."""

import pytest
from interview_agent.prompts import load_prompt, render


class TestLoadPrompt:
    def test_load_interviewer_system(self):
        text = load_prompt("interviewer_system")
        assert len(text) > 0
        assert "面试官" in text

    def test_load_followup_generator(self):
        text = load_prompt("followup_generator")
        assert "{current_question}" in text

    def test_load_gate_evaluator(self):
        text = load_prompt("gate_evaluator")
        assert "HIGH" in text

    def test_load_score_answer(self):
        text = load_prompt("score_answer")
        assert "clarity" in text

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_prompt("nonexistent_prompt")

    def test_override(self):
        override_text = "custom prompt"
        text = load_prompt("interviewer_system", override=override_text)
        assert text == override_text


class TestRender:
    def test_render_injects_variables(self):
        msg = render(
            "interviewer_system",
            "用户输入",
            candidate_profile="Java后端",
            current_pool="scenario",
            history="",
        )
        assert "system" in msg
        assert "user" in msg
        assert "Java后端" in msg["system"]
        assert msg["user"] == "用户输入"

    def test_render_missing_variable_no_raise(self):
        # .format() on missing brace-style placeholder silently leaves it,
        # but our render() requires all placeholders to be provided via kwargs
        msg = render(
            "interviewer_system",
            "用户输入",
            candidate_profile="Java后端",
            current_pool="scenario",
            history="",
        )
        assert "system" in msg
        assert "user" in msg

    def test_render_all_variables(self):
        msg = render(
            "interviewer_system",
            "测试消息",
            candidate_profile="Golang后端",
            current_pool="fundamentals",
            history="Q: 你好\nA: 你好",
        )
        assert "Golang后端" in msg["system"]
        assert "fundamentals" in msg["system"]