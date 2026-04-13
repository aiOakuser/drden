"""
Regenerate multi-platform social copy from live Global Designer Hub context + OpenAI.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


def gather_site_context_text(
    *,
    max_collections: int = 6,
    max_designers: int = 8,
    max_events: int = 5,
) -> str:
    """Build a plain-text brief from DB (no PII beyond public-facing fields)."""
    from designer_portfolio.models import Collection, DesignerProfile, Event

    chunks: list[str] = [
        "Brand: Global Designer Hub — marketplace for fashion/design talent, portfolios, "
        "collections, events, in-platform messaging, DesignerBot, site builder for designers.\n"
    ]

    cols = (
        Collection.objects.filter(published=True)
        .order_by("-created_at")[:max_collections]
    )
    if cols:
        chunks.append("Recent public collections (name, year, season, short description):\n")
        for c in cols:
            desc = (c.description or "").strip().replace("\n", " ")
            if len(desc) > 220:
                desc = desc[:217] + "..."
            chunks.append(
                f"- {c.name} ({c.year}{(' · ' + c.season) if c.season else ''}): {desc or '—'}\n"
            )
    else:
        chunks.append("Collections: none published in DB snapshot.\n")

    profiles = DesignerProfile.objects.select_related("user").order_by("-updated_at")[
        :max_designers
    ]
    if profiles:
        chunks.append("Designer specialties (public-facing, no emails):\n")
        for p in profiles:
            spec = (p.specialization or "").strip()
            loc = p.location_display or (p.region_area or "").strip()
            uname = getattr(p.user, "username", "") or "designer"
            chunks.append(f"- @{uname}: {spec or 'designer'}{(' · ' + loc) if loc else ''}\n")
    else:
        chunks.append("Designer profiles: none in DB snapshot.\n")

    evs = Event.objects.order_by("-event_date", "-created_at")[:max_events]
    if evs:
        chunks.append("Upcoming / recent events:\n")
        for e in evs:
            when = e.event_date.isoformat() if e.event_date else "TBA"
            loc = (e.location or e.venue or "").strip()
            desc = (e.description or "").strip().replace("\n", " ")
            if len(desc) > 160:
                desc = desc[:157] + "..."
            pop = " (popup)" if e.is_popup else ""
            chunks.append(f"- {e.title}{pop} · {when}{(' · ' + loc) if loc else ''}: {desc or '—'}\n")
    else:
        chunks.append("Events: none in DB snapshot.\n")

    base = (getattr(settings, "BASE_URL_SERVER", None) or "").strip()
    if base:
        chunks.append(f"Canonical site URL for CTAs: {base.rstrip('/')}\n")

    return "".join(chunks)


def _strip_code_fence(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            inner = parts[1]
            if inner.lstrip().startswith("json"):
                inner = inner.lstrip()[4:].lstrip()
            return inner.strip()
    return text


def _parse_json_object(raw: str) -> dict[str, Any]:
    text = _strip_code_fence(raw)
    return json.loads(text)


def generate_platforms_json(*, context: str) -> tuple[dict[str, Any], str]:
    """
    Call OpenAI; return (payload dict, model name).
    payload keys: instagram_caption, instagram_hashtags, linkedin_post, x_post,
    suggested_cta, notes_for_designer
    """
    api_key = (getattr(settings, "OPENAI_API_KEY", None) or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from openai import OpenAI

    model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)

    system = """You write social posts for Global Designer Hub (fashion/design talent & portfolios).
Return ONLY a single JSON object (no markdown) with these exact keys:
- "instagram_caption" (string, <= 2100 characters, line breaks allowed)
- "instagram_hashtags" (array of 6-14 strings, each starting with #)
- "linkedin_post" (string, <= 2800 characters, short paragraphs, professional)
- "x_post" (string, <= 260 characters for X/Twitter)
- "suggested_cta" (string, one line, e.g. link text + why click)
- "notes_for_designer" (string, optional internal reminder: tone, timing, asset ideas)

Rules:
- Warm, confident, inclusive; avoid hype numbers you cannot verify.
- Use only facts implied by CONTEXT; if context is thin, write strong evergreen copy about the hub's purpose (hire designers, living portfolios, collections, events, safe in-app collaboration).
- Do not claim discounts or legal promises unless stated in CONTEXT.
- No hashtags inside instagram_caption body; put all hashtags only in instagram_hashtags."""

    user = f"CONTEXT:\n{context}\n\nProduce fresh variants (not generic templates)."

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.85,
        max_tokens=2200,
        response_format={"type": "json_object"},
    )
    raw = (response.choices[0].message.content or "").strip()
    data = _parse_json_object(raw)
    required = (
        "instagram_caption",
        "instagram_hashtags",
        "linkedin_post",
        "x_post",
        "suggested_cta",
        "notes_for_designer",
    )
    for key in required:
        if key not in data:
            raise ValueError(f"Missing JSON key: {key}")
    if not isinstance(data["instagram_hashtags"], list):
        raise ValueError("instagram_hashtags must be an array")
    return data, model


def regenerate_bundle(*, save: bool = True):
    """
    Gather context, call OpenAI, optionally persist SocialContentBundle.
    Returns the SocialContentBundle instance (saved or unsaved).
    """
    from marketing.models import SocialContentBundle

    context = gather_site_context_text()
    try:
        platforms, model_used = generate_platforms_json(context=context)
        bundle = SocialContentBundle(
            source_context=context[:50000],
            platforms=platforms,
            model_used=model_used,
            success=True,
            error="",
        )
    except Exception as e:
        logger.exception("social_regenerator: failed: %s", e)
        bundle = SocialContentBundle(
            source_context=context[:50000],
            platforms={},
            model_used=getattr(settings, "OPENAI_MODEL", "") or "",
            success=False,
            error=str(e)[:8000],
        )
    if save:
        bundle.save()
    return bundle
