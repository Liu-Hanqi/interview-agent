"""LLM client wrapper — DeepSeek via OpenAI-compatible endpoint."""

import os
from dataclasses import dataclass
from typing import Literal

import httpx
from openai import OpenAI


@dataclass
class LLMResponse:
    raw: str
    usage: dict


def _get_client() -> OpenAI:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not set")
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
        http_client=httpx.Client(trust_env=False),
    )


def generate(
    system: str,
    user: str,
    model: Literal["claude-sonnet", "claude-haiku"] = "claude-sonnet",
    json_mode: bool = False,
) -> LLMResponse:
    """Call DeepSeek API via OpenAI-compatible endpoint.

    DeepSeek deepseek-chat supports system messages natively.
    json_mode: request structured JSON response (model will comply if system asks for it).
    """
    client = _get_client()

    # DeepSeek model mapping — both map to deepseek-chat for quality
    model_map = {
        "claude-sonnet": "deepseek-chat",
        "claude-haiku": "deepseek-chat",
    }
    actual_model = model_map.get(model, "deepseek-chat")

    extra_kwargs = {}
    if json_mode:
        # DeepSeek requires the word "json" in the prompt
        extra_kwargs["response_format"] = {"type": "json_object"}
        # Inject json requirement into the user message so the API accepts it
        user = f"{user}\n\n请以 JSON 格式输出。"

    message = client.chat.completions.create(
        model=actual_model,
        max_tokens=1024,
        temperature=0.7,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        timeout=60.0,
        **extra_kwargs,
    )

    raw = message.choices[0].message.content or ""

    return LLMResponse(
        raw=raw,
        usage={
            "input_tokens": message.usage.prompt_tokens if message.usage else 0,
            "output_tokens": message.usage.completion_tokens if message.usage else 0,
        },
    )