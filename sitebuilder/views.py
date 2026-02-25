"""Site Builder views — editor, save, publish, AI generation, public view."""
import json
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .models import BuilderPage, BuilderSite


@login_required
def builder_sites_list(request):
    """List all builder sites for the current user."""
    sites = BuilderSite.objects.filter(owner=request.user)
    return render(request, "sitebuilder/sites_list.html", {"sites": sites})


@login_required
def builder_site_create(request):
    """Create a new builder site."""
    if request.method == "POST":
        name = (request.POST.get("name") or "My Site").strip()[:120]
        site = BuilderSite.objects.create(owner=request.user, name=name)
        page = BuilderPage.objects.create(
            site=site,
            title="Home",
            is_home=True,
            meta_title=name,
            meta_description=f"Welcome to {name}",
        )
        return redirect("builder_editor_page", site_slug=site.slug, page_id=page.id)
    return redirect("builder_sites_list")


@login_required
def builder_editor(request, site_slug, page_id=None):
    """Visual drag-and-drop builder editor (GrapesJS)."""
    site = get_object_or_404(BuilderSite, slug=site_slug, owner=request.user)
    pages = site.pages.all()
    page = None
    if page_id:
        page = get_object_or_404(BuilderPage, pk=page_id, site=site)
    else:
        page = pages.filter(is_home=True).first() or pages.first()
        if page:
            return redirect("builder_editor_page", site_slug=site_slug, page_id=page.id)
        else:
            page = BuilderPage.objects.create(
                site=site,
                title="Home",
                is_home=True,
            )
            return redirect("builder_editor_page", site_slug=site_slug, page_id=page.id)

    context = {
        "site": site,
        "page": page,
        "pages": pages,
        "public_url": request.build_absolute_uri(
            reverse("builder_public_page", args=[site.slug, page.slug or "index"])
        ),
        "page_data_json": json.dumps({
            "html": page.html_content or "",
            "css": page.css_content or "",
            "meta_title": page.meta_title or "",
            "meta_description": page.meta_description or "",
        }),
    }
    return render(request, "sitebuilder/editor.html", context)


@login_required
@require_POST
def builder_save_page(request, site_slug, page_id):
    """Save page content from GrapesJS."""
    site = get_object_or_404(BuilderSite, slug=site_slug, owner=request.user)
    page = get_object_or_404(BuilderPage, pk=page_id, site=site)

    try:
        data = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    page.html_content = data.get("html", page.html_content)
    page.css_content = data.get("css", page.css_content)
    page.block_data = data.get("blockData", page.block_data or {})
    page.meta_title = (data.get("meta", {}).get("title") or page.meta_title or "")[:70]
    page.meta_description = (data.get("meta", {}).get("description") or page.meta_description or "")[:160]
    page.animation_config = data.get("animationConfig", page.animation_config or {})
    page.save()
    return JsonResponse({"status": "ok", "saved_at": page.updated_at.isoformat()})


@login_required
@require_POST
def builder_ai_generate(request, site_slug):
    """AI-assisted layout generation from text prompt."""
    site = get_object_or_404(BuilderSite, slug=site_slug, owner=request.user)
    try:
        data = json.loads(request.body or "{}")
        prompt = (data.get("prompt") or "").strip()
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not prompt:
        return JsonResponse({"error": "Prompt is required"}, status=400)

    api_key = getattr(settings, "OPENAI_API_KEY", None)
    if not api_key:
        return JsonResponse({"error": "AI not configured"}, status=503)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")

        system_prompt = """You are a web layout designer for fashion portfolios and landing pages.
Given a user's prompt, output a JSON structure for a webpage with these block types:
- hero: {headline, subheadline, ctaText, ctaUrl, backgroundImage?, backgroundColor?}
- text: {content (HTML), align?}
- image: {src, alt, caption?}
- gallery: {images: [{src,alt}], columns?}
- features: {items: [{title, description, icon?}]}
- cta: {headline, buttonText, buttonUrl}
- footer: {copyright, links?}

Return ONLY valid JSON, no markdown. Example structure:
{"blocks":[{"type":"hero","data":{"headline":"My Portfolio","subheadline":"Fashion Designer"}},{"type":"text","data":{"content":"<p>About me...</p>"}}]}
"""
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
        )
        raw = (response.choices[0].message.content or "").strip()
        # Strip markdown code blocks if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        blocks_data = json.loads(raw)
        return JsonResponse({"status": "ok", "blocks": blocks_data.get("blocks", [])})
    except json.JSONDecodeError as e:
        return JsonResponse({"error": f"AI returned invalid JSON: {e}"}, status=502)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@require_GET
def builder_public_page(request, site_slug, page_slug="index"):
    """Public view of a published builder page."""
    site = get_object_or_404(BuilderSite, slug=site_slug, published=True)
    page = get_object_or_404(
        BuilderPage,
        site=site,
        slug=page_slug,
    )
    context = {
        "site": site,
        "page": page,
    }
    return render(request, "sitebuilder/public_page.html", context)


@login_required
@require_POST
def builder_publish(request, site_slug):
    """Publish or unpublish a site."""
    site = get_object_or_404(BuilderSite, slug=site_slug, owner=request.user)
    site.published = not site.published
    site.save()
    return JsonResponse({"status": "ok", "published": site.published})
