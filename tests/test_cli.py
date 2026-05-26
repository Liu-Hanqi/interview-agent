"""Tests for the CLI module."""

from interview_agent.cli.main import POOL_DISPLAY


def test_pool_display():
    assert "algorithm" in POOL_DISPLAY
    assert "fundamentals" in POOL_DISPLAY
    assert "scenario" in POOL_DISPLAY
    assert "50%" in POOL_DISPLAY["fundamentals"]