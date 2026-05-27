"""LLM client wrapper — MiniMax via Anthropic-compatible endpoint."""

import os
from dataclasses import dataclass
from typing import Literal

import anthropic


@dataclass
class LLMResponse:
    raw: str
    usage: dict


def _get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("MINIMAX_CN_API_KEY") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("MINIMAX_CN_API_KEY not set")
    base_url = os.environ.get(
        "MINIMAX_CN_BASE_URL", "https://api.minimaxi.com/anthropic"
    )
    return anthropic.Anthropic(api_key=api_key, base_url=base_url)


def generate(
    system: str,
    user: str,
    model: Literal["claude-sonnet", "claude-haiku"] = "claude-sonnet",
    json_mode: bool = False,
) -> LLMResponse:
    """Call MiniMax API via Anthropic-compatible endpoint.

    Note: MiniMax's Anthropic-compatible endpoint does not correctly handle the
    separate system= parameter — system content is prepended to the user message
    instead (as a single user turn), which produces the expected behavior.
    """
    client = _get_client()

    model_map = {
        "claude-sonnet": "MiniMax-M2.7",
        "claude-haiku": "MiniMax-M2.7",
    }
    actual_model = model_map.get(model, "MiniMax-M2.7")

    extra_kwargs = {}
    if json_mode:
        # MiniMax does not support response_format; prompt instructs JSON instead
        pass

    # Use system= parameter directly — MiniMax respects it correctly
    message = client.messages.create(
        model=actual_model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": user}],
        **extra_kwargs,
    )

    # MiniMax may return ThinkingBlock + TextBlock; find the text answer
    text_block = next(
        (b for b in message.content if b.type == "text"),
        message.content[-1] if message.content else None,
    )
    raw = text_block.text if text_block else ""

    return LLMResponse(
        raw=raw,
        usage={
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        },
    )