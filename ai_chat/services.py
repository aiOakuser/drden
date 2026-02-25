"""
AI Chat services: OpenAI streaming, message building, and usage tracking.
"""
import json
import logging
from typing import Iterator

from django.conf import settings

logger = logging.getLogger(__name__)


def stream_openai_chat(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2000,
) -> Iterator[str]:
    """
    Stream OpenAI Chat Completions response as SSE-style chunks.
    Yields strings in format: "data: {...}\n\n"
    Uses settings.OPENAI_API_KEY.
    """
    api_key = getattr(settings, "OPENAI_API_KEY", "") or ""
    if not api_key or not api_key.strip():
        yield _sse_data({"error": "OpenAI API key not configured"})
        return

    model = model or getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                yield _sse_data({"delta": content})

        yield _sse_data({"done": True})

    except ImportError:
        logger.warning("ai_chat: openai library not installed. Run: pip install openai")
        yield _sse_data({"error": "AI service unavailable"})
    except Exception as e:
        logger.exception("ai_chat: OpenAI stream error: %s", e)
        yield _sse_data({"error": str(e)})


def _sse_data(obj: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(obj)}\n\n"
