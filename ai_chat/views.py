"""
AI Chat API views: SSE streaming endpoint.
"""
import json
import logging
import uuid
from django.conf import settings
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import requires_csrf_token
from django.views.decorators.http import require_GET, require_POST

from .services import stream_openai_chat

logger = logging.getLogger(__name__)


def _build_designer_messages(request, user_message: str, context_page: str, language: str):
    """Build message list for Designer AI chat. Delegates to designer_portfolio."""
    from designer_portfolio.models import DesignerAISession, DesignerAIMessage, DocPage
    from django.db.models import Q
    from designer_portfolio.ai.chat_assistant import get_system_prompt

    session_id = request.COOKIES.get("designer_ai_session")
    session = None
    if session_id:
        try:
            session = DesignerAISession.objects.get(session_id=session_id)
        except DesignerAISession.DoesNotExist:
            pass

    if not session:
        session = DesignerAISession.objects.create(
            user=request.user if request.user.is_authenticated else None,
            session_id=str(uuid.uuid4()),
            language=language,
        )

    system_prompt = get_system_prompt()
    if context_page:
        context_info = f"\n\nUser is currently on page: {context_page}"
        if "dashboard" in context_page:
            context_info += "\nThey are in the dashboard area."
        if "design" in context_page:
            context_info += "\nThey are working with designs."
        if "collection" in context_page:
            context_info += "\nThey are working with collections."
        system_prompt += context_info

    messages = [{"role": "system", "content": system_prompt}]

    try:
        rag_docs = list(
            DocPage.objects.filter(published=True, language=language)
            .filter(
                Q(content__icontains=user_message)
                | Q(title__icontains=user_message)
                | Q(tags__icontains=user_message)
            )[:3]
        )
        if rag_docs:
            rag_context = "\n\n--- Documentation Context ---\n\n"
            rag_context += "\n\n---\n\n".join(
                f"Title: {doc.title}\nContent: {doc.content[:500]}...\nLink: /docs/{doc.category}/{doc.slug}/"
                for doc in rag_docs
            )
            messages.append({"role": "system", "content": rag_context})
    except Exception:
        pass

    history_qs = (
        DesignerAIMessage.objects.filter(session=session)
        .exclude(role="system")
        .order_by("-created_at")[:10]
    )
    for msg in reversed(list(history_qs)):
        if msg.role in ("user", "assistant"):
            messages.append({"role": msg.role, "content": msg.content})

    messages.append({"role": "user", "content": user_message})
    return messages, session


def _save_designer_messages(session, user_message: str, assistant_content: str):
    """Persist user and assistant messages for history."""
    from designer_portfolio.models import DesignerAIMessage

    DesignerAIMessage.objects.create(session=session, role="user", content=user_message)
    DesignerAIMessage.objects.create(
        session=session, role="assistant", content=assistant_content
    )


@require_POST
@requires_csrf_token
def stream_chat(request):
    """
    SSE streaming endpoint for AI chat.
    Flow: Browser → POST /api/ai/stream → OpenAI (stream) → stream back to browser.

    Request body (JSON):
    {
        "message": "user message",
        "context_page": "/dashboard/designs/",
        "current_url": "https://...",
        "language": "en"
    }

    Response: text/event-stream with data: {"delta": "..."} chunks, ending with data: {"done": true}
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return _json_error("Invalid JSON", 400)

    user_message = data.get("message", "").strip()
    if not user_message:
        return _json_error("Message is required", 400)

    context_page = data.get("context_page", "")
    language = data.get("language", "en")

    api_key = getattr(settings, "OPENAI_API_KEY", "") or ""
    if not api_key or not api_key.strip():
        return _json_error("AI service not configured", 503)

    try:
        messages, session = _build_designer_messages(
            request, user_message, context_page, language
        )
    except Exception as e:
        if settings.DEBUG:
            raise
        return _json_error("Failed to build chat context", 500)

    def generate():
        full_content = []
        try:
            for chunk in stream_openai_chat(messages):
                yield chunk
                if chunk.startswith("data: "):
                    try:
                        json_str = chunk[6:].strip()
                        if json_str and json_str != "[DONE]":
                            obj = json.loads(json_str)
                            if "delta" in obj:
                                full_content.append(obj["delta"])
                    except (json.JSONDecodeError, ValueError):
                        pass
            content = "".join(full_content)
            if content and session:
                try:
                    _save_designer_messages(session, user_message, content)
                except Exception:
                    logger.exception("ai_chat: failed to persist Designer AI messages")
        except GeneratorExit:
            pass

    response = StreamingHttpResponse(
        generate(),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache"
    # nginx only — tells proxy not to buffer SSE (harmless if not behind nginx).
    response["X-Accel-Buffering"] = "no"
    # Do not set Connection: keep-alive — WSGI forbids hop-by-hop headers (breaks runserver).

    if session:
        response.set_cookie(
            "designer_ai_session",
            str(session.session_id),
            max_age=60 * 60 * 24 * 30,
            samesite="Lax",
        )

    return response


def _json_error(message: str, status: int):
    from django.http import JsonResponse
    return JsonResponse({"success": False, "error": message}, status=status)


@require_GET
def designer_ai_session_messages(request, session_id: str):
    """
    Return persisted Designer AI messages for the browser session cookie.
    Used by the chat widget when opening the panel (load history).
    Only returns data when the session_id matches designer_ai_session cookie (no cross-session reads).
    """
    from django.http import JsonResponse

    cookie_sid = (request.COOKIES.get("designer_ai_session") or "").strip()
    if not cookie_sid or cookie_sid != session_id:
        return JsonResponse({"messages": []})

    from designer_portfolio.models import DesignerAISession, DesignerAIMessage

    try:
        session = DesignerAISession.objects.get(session_id=session_id)
    except DesignerAISession.DoesNotExist:
        return JsonResponse({"messages": []})

    qs = (
        DesignerAIMessage.objects.filter(session=session)
        .exclude(role="system")
        .order_by("created_at")
    )
    messages = [{"role": m.role, "content": m.content} for m in qs]
    return JsonResponse({"messages": messages})
