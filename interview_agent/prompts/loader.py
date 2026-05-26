"""
Prompt loader with runtime override support.
"""

from pathlib import Path
from typing import Optional


def _get_prompt_dir() -> Path:
    return Path(__file__).parent


def load_prompt(name: str, override: Optional[str] = None) -> str:
    """Load a prompt from file, with optional runtime override.

    Args:
        name: prompt filename without .txt (e.g. "interviewer_system")
        override: if provided, use this string instead of file content

    Returns:
        prompt text
    """
    if override is not None:
        return override
    path = _get_prompt_dir() / f"{name}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def render(system_name: str, user_message: str, **kwargs) -> dict:
    """Render a prompt with variables injected into both system and user.

    Returns a dict with 'system' and 'user' keys suitable for
    anthropic API calls.

    Args:
        system_name: prompt file name without .txt
        user_message: user message template with {var} placeholders
        **kwargs: variable values to inject into templates
    """
    system_raw = load_prompt(system_name)
    # Strip YAML frontmatter before injecting variables
    lines = system_raw.split("\n")
    if lines[0].strip() == "---":
        # Find closing ---
        end = 1
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                end = i
                break
        body = "\n".join(lines[end + 1 :])
    else:
        body = system_raw

    system = body.format(**kwargs)
    user = user_message.format(**kwargs)
    return {"system": system, "user": user}