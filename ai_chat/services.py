"""
AI Chat services: OpenAI streaming, message building, and usage tracking.
"""
import json
import logging
from typing import Iterator

from django.conf import settings

logger = logging.getLogger(__name__)


def build_openai_client(api_key: str):
    """Shared OpenAI client with timeouts suited to chat streaming (avoids 'Request timed out')."""
    from openai import OpenAI

    read_s = float(getattr(settings, "OPENAI_TIMEOUT", 300))
    read_s = max(60.0, read_s)
    org = getattr(settings, "OPENAI_ORGANIZATION", None)
    base_url = getattr(settings, "OPENAI_BASE_URL", None)
    client_kw: dict = {"api_key": api_key}
    if org:
        client_kw["organization"] = org
    if base_url:
        client_kw["base_url"] = base_url
    try:
        import httpx

        client_kw["timeout"] = httpx.Timeout(connect=30.0, read=read_s, write=120.0, pool=60.0)
        return OpenAI(**client_kw)
    except Exception:
        client_kw["timeout"] = read_s
        return OpenAI(**client_kw)


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
        client = build_openai_client(api_key)
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
        _rate_limit_type = None
        try:
            from openai import RateLimitError as _RateLimitError

            _rate_limit_type = _RateLimitError
        except ImportError:
            pass

        if _rate_limit_type is not None and isinstance(e, _rate_limit_type):
            low = str(e).lower()
            if "insufficient_quota" in low or "quota" in low or "billing" in low:
                logger.warning("ai_chat: OpenAI insufficient quota / billing (streaming)")
            else:
                logger.warning("ai_chat: OpenAI rate limit (streaming): %s", e)
            yield _sse_data(
                {
                    "error": (
                        "AI is unavailable: your OpenAI project has no usable quota or billing. "
                        "Add payment or credits at https://platform.openai.com/account/billing "
                        "or set a valid OPENAI_API_KEY."
                    )
                }
            )
            return

        logger.exception("ai_chat: OpenAI stream error: %s", e)
        msg = str(e)
        low = msg.lower()
        if "timed out" in low or "timeout" in low:
            msg = (
                "The AI request timed out (slow network or long reply). Try a shorter question, "
                "or increase OPENAI_TIMEOUT in your environment (and nginx proxy_read_timeout if you use a reverse proxy)."
            )
        yield _sse_data({"error": msg})


def _sse_data(obj: dict) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(obj)}\n\n"
