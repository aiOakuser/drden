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


def gather_ios_app_promo_context_text() -> str:
    """Facts for Instagram posts promoting the designer iPhone app (settings + product copy)."""
    app_name = (getattr(settings, "IOS_APP_NAME", None) or "GlobalDesignerHub").strip()
    store = (getattr(settings, "IOS_APP_STORE_URL", None) or "").strip()
    testflight = (getattr(settings, "IOS_TESTFLIGHT_URL", None) or "").strip()
    base = (getattr(settings, "BASE_URL_SERVER", None) or "").strip()
    lines = [
        "Product: Global Designer Hub — designer-facing iPhone app for the same account as the website.\n",
        f"App display name: {app_name}\n",
    ]
    if store:
        lines.append(f"App Store URL (use in CTA / first comment): {store}\n")
    if testflight:
        lines.append(f"TestFlight URL (beta): {testflight}\n")
    if base:
        lines.append(f"Marketing / download page on web: {base.rstrip('/')}/iphone-app/\n")
    ig = (getattr(settings, "GDH_INSTAGRAM_URL", None) or "").strip()
    if ig:
        lines.append(f"Official brand Instagram: {ig}\n")
    lines.extend(
        [
            "Hero value props:\n",
            "- Review tech packs and approve updates on the go.\n",
            "- Message designers with secure threads and shared files.\n",
            "- Stay on schedule with collection and event alerts.\n",
            "Feature highlights:\n",
            "- Portfolio access: lookbooks, tech packs, collections on iPhone.\n",
            "- Mobile uploads: studio progress shots attached to projects.\n",
            "- Instant messaging: in-app chat and notifications.\n",
            "- Event reminders: fashion week schedules and meetups.\n",
            "Requirements: iOS 16+. Wi-Fi recommended for first download.\n",
            "Task: write Instagram-ready promo. Encourage download; stay truthful to the facts above.\n",
        ]
    )
    return "".join(lines)


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


def generate_instagram_app_promo_json(*, context: str) -> tuple[dict[str, Any], str]:
    """
    Instagram-focused pack for the designer iPhone app + prompt for an original “AI designer” visual.
    """
    api_key = (getattr(settings, "OPENAI_API_KEY", None) or "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")

    from openai import OpenAI

    model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
    client = OpenAI(api_key=api_key)

    system = """You are a senior social creative for a fashion-tech brand. The client promotes their
iPhone app for designers (Global Designer Hub). Return ONLY valid JSON (no markdown) with these keys:
- "instagram_caption" (string, <= 1900 chars; line breaks ok; NO hashtags inside this string)
- "instagram_hashtags" (array of 8-16 strings, each starting with #, mix branded + discovery tags)
- "instagram_carousel_slides" (array of 5-7 short strings; each is on-slide copy for a square carousel, slide 1 = hook)
- "instagram_stories_bullets" (array of 4-6 very short lines for story text overlays, sequential)
- "ai_designer_image_prompt" (string, 400-900 chars): a detailed image-generation prompt for an ORIGINAL fictional
  fashion-creative spokesperson (no celebrity, no real person). Describe look, wardrobe, pose, lighting, and include
  holding or beside an iPhone showing a generic “portfolio grid” UI (no readable Apple trademarks, no App Store logo).
  Style: premium editorial, inclusive, modern studio or city soft light.
- "first_comment" (string): pinned-style first comment with clear download CTA; MUST include the App Store URL from
  CONTEXT if one was provided; otherwise say “link in bio” / site path only.
- "notes_for_social_manager" (string): best time to post, reel vs carousel suggestion, compliance reminders.

Rules: truthful, no fake ratings or “#1 app” claims, no invented features not in CONTEXT."""

    user = f"CONTEXT:\n{context}\n\nGenerate one fresh campaign variant."

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.9,
        max_tokens=2600,
        response_format={"type": "json_object"},
    )
    raw = (response.choices[0].message.content or "").strip()
    data = _parse_json_object(raw)
    required = (
        "instagram_caption",
        "instagram_hashtags",
        "instagram_carousel_slides",
        "instagram_stories_bullets",
        "ai_designer_image_prompt",
        "first_comment",
        "notes_for_social_manager",
    )
    for key in required:
        if key not in data:
            raise ValueError(f"Missing JSON key: {key}")
    for list_key in ("instagram_hashtags", "instagram_carousel_slides", "instagram_stories_bullets"):
        if not isinstance(data[list_key], list):
            raise ValueError(f"{list_key} must be an array")
    return data, model


def regenerate_bundle(*, save: bool = True, bundle_kind: str | None = None):
    """
    Gather context, call OpenAI, optionally persist SocialContentBundle.
    bundle_kind: SocialContentBundle.Kind value (default: hub_social).
    Returns the SocialContentBundle instance (saved or unsaved).
    """
    from marketing.models import SocialContentBundle

    kind = bundle_kind or SocialContentBundle.Kind.HUB_SOCIAL

    if kind == SocialContentBundle.Kind.INSTAGRAM_APP:
        context = gather_ios_app_promo_context_text()
        try:
            platforms, model_used = generate_instagram_app_promo_json(context=context)
            bundle = SocialContentBundle(
                bundle_kind=kind,
                source_context=context[:50000],
                platforms=platforms,
                model_used=model_used,
                success=True,
                error="",
            )
        except Exception as e:
            logger.exception("social_regenerator instagram_app: failed: %s", e)
            bundle = SocialContentBundle(
                bundle_kind=kind,
                source_context=context[:50000],
                platforms={},
                model_used=getattr(settings, "OPENAI_MODEL", "") or "",
                success=False,
                error=str(e)[:8000],
            )
        if save:
            bundle.save()
        return bundle

    context = gather_site_context_text()
    try:
        platforms, model_used = generate_platforms_json(context=context)
        bundle = SocialContentBundle(
            bundle_kind=SocialContentBundle.Kind.HUB_SOCIAL,
            source_context=context[:50000],
            platforms=platforms,
            model_used=model_used,
            success=True,
            error="",
        )
    except Exception as e:
        logger.exception("social_regenerator: failed: %s", e)
        bundle = SocialContentBundle(
            bundle_kind=SocialContentBundle.Kind.HUB_SOCIAL,
            source_context=context[:50000],
            platforms={},
            model_used=getattr(settings, "OPENAI_MODEL", "") or "",
            success=False,
            error=str(e)[:8000],
        )
    if save:
        bundle.save()
    return bundle
