"""Prompt loader with runtime override support."""

import re
from pathlib import Path
from typing import Any, Optional


def _get_prompt_dir() -> Path:
    return Path(__file__).parent


def load_prompt(name: str, override: Optional[str] = None) -> str:
    """Load a prompt from file, with optional runtime override."""
    if override is not None:
        return override
    path = _get_prompt_dir() / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def render(system_name: str, user_message: str, **kwargs: Any) -> dict[str, str]:
    """Render a prompt with variables injected.

    Uses regex substitution instead of str.format() to avoid conflicts
    with JSON/brace characters in variable values.
    """
    body_raw = load_prompt(system_name)

    # Strip YAML frontmatter
    lines = body_raw.split("\n")
    if lines[0].strip() == "---":
        end = next((i for i, l in enumerate(lines[1:], 1) if l.strip() == "---"), None)
        body = "\n".join(lines[end + 1 :]) if end is not None else body_raw
    else:
        body = body_raw

    # Replace {var} placeholders via regex
    def replace_placeholder(match: re.Match) -> str:
        key = match.group(1)
        if key not in kwargs:
            raise KeyError(key)
        return str(kwargs[key])

    system = re.sub(r"\{(\w+)\}", replace_placeholder, body)
    user = re.sub(r"\{(\w+)\}", replace_placeholder, user_message)

    return {"system": system, "user": user}