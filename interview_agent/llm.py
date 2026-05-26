"""LLM client wrapper for Anthropic API."""

import os
from dataclasses import dataclass
from typing import Literal

from anthropic import Anthropic


@dataclass
class LLMResponse:
    raw: str
    usage: dict


def _get_client() -> Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    return Anthropic(api_key=api_key)


def generate(
    system: str,
    user: str,
    model: Literal["claude-sonnet", "claude-haiku"] = "claude-sonnet",
    json_mode: bool = False,
) -> LLMResponse:
    """Call Anthropic API and return raw response.

    Args:
        system: system prompt
        user: user message
        model: which model to use
        json_mode: if True, ask model to output JSON and parse it
    """
    client = _get_client()

    actual_model = {
        "claude-sonnet": "claude-sonnet-4-20250514",
        "claude-haiku": "claude-3-haiku-20250517",
    }.get(model, model)

    extra_kwargs = {}
    if json_mode:
        extra_kwargs["response_format"] = {"type": "json_object"}

    message = client.messages.create(
        model=actual_model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
        **extra_kwargs,
    )

    return LLMResponse(
        raw=message.content[0].text,
        usage={
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        },
    )