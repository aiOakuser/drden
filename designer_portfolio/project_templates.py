import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Tuple

from django.core.exceptions import AppRegistryNotReady, ImproperlyConfigured
from django.core.serializers.json import DjangoJSONEncoder
from django.db import OperationalError, ProgrammingError


class ProjectTemplateNotFound(Exception):
    """Raised when a requested project template could not be located."""


PROJECT_TEMPLATE_PATH = Path(__file__).resolve().parent / "data" / "project_templates.json"


def _normalize_template(template: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure optional keys exist so downstream rendering logic can rely on them."""
    template.setdefault("summary", [])
    template.setdefault("thumbnail", {})
    template.setdefault("cover", {})
    template.setdefault("stages", [])
    template.setdefault("productBlocks", [])
    template.setdefault("productSpec", {})
    return template


def _serialize_template_object(template) -> Dict[str, Any]:
    """Convert a Template ORM object into the payload used by the UI/API."""
    cover = template.metadata.get("cover") or template.cover
    if not isinstance(cover, dict):
        cover = {}
    thumbnail = template.metadata.get("thumbnail") or {}
    if not isinstance(thumbnail, dict):
        thumbnail = {}
    category = template.metadata.get("category", "")

    stages = []
    for stage in template.stages.all():
        stages.append(
            {
                "id": f"{template.id}:stage:{stage.stage_index}",
                "stageNumber": stage.stage_index,
                "title": stage.title,
                "layoutHint": stage.layout_hint,
                "defaultBullets": stage.default_items,
                "defaultItems": stage.default_items,
            }
        )

    product_blocks = []
    for block in template.product_blocks.all():
        schema = block.details_schema or {}
        product_blocks.append(
            {
                "id": f"{template.id}:block:{block.block_index}",
                "blockIndex": block.block_index,
                "label": block.label,
                "titlePlaceholder": block.title_placeholder,
                "codePlaceholder": block.code_placeholder,
                "defaultViews": block.default_views,
                "detailsTemplate": schema,
            }
        )

    product_spec = {}
    if product_blocks:
        first_block = product_blocks[0]
        details_template = first_block.get("detailsTemplate") or {}
        product_spec = {
            "title": first_block.get("titlePlaceholder") or "Product Spec",
            "layoutHint": details_template.get("layoutHint", ""),
            "fields": details_template.get("fields", []),
        }

    return {
        "id": template.id,
        "name": template.name,
        "category": category,
        "layoutKey": template.layout_key,
        "thumbnail": thumbnail,
        "summary": template.summary or [],
        "cover": {
            "titlePlaceholder": cover.get("titlePlaceholder") or template.cover_title_placeholder,
            "subtitle": cover.get("subtitle") or cover.get("subtitlePlaceholder") or template.cover_subtitle_placeholder,
            "subtitlePlaceholder": cover.get("subtitlePlaceholder") or template.cover_subtitle_placeholder,
        },
        "stages": stages,
        "productBlocks": product_blocks,
        "productSpec": product_spec,
    }


def _load_templates_from_db() -> List[Dict[str, Any]]:
    try:
        from .models import Template
    except AppRegistryNotReady:
        return []

    try:
        templates = (
            Template.objects.all()
            .prefetch_related("stages", "product_blocks")
            .order_by("name", "id")
        )
    except (ImproperlyConfigured, OperationalError, ProgrammingError):
        return []

    return [_serialize_template_object(template) for template in templates]


def _load_templates_from_disk() -> List[Dict[str, Any]]:
    if not PROJECT_TEMPLATE_PATH.exists():
        return []

    with PROJECT_TEMPLATE_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    templates = payload.get("templates", [])
    return [_normalize_template(t) for t in templates]


@lru_cache(maxsize=1)
def load_project_templates() -> List[Dict[str, Any]]:
    """Load and cache the list of project templates, preferring the database."""
    templates = _load_templates_from_db()
    if templates:
        return templates
    return _load_templates_from_disk()


def refresh_project_template_cache() -> None:
    """Clear the in-memory cache so subsequent calls read fresh data."""
    load_project_templates.cache_clear()  # type: ignore[attr-defined]


def get_project_template(template_id: str) -> Dict[str, Any]:
    """Return a single template dictionary or raise ProjectTemplateNotFound."""
    for template in load_project_templates():
        if template.get("id") == template_id:
            return template
    raise ProjectTemplateNotFound(f"Template '{template_id}' was not found.")


def serialize_templates_for_client() -> str:
    """Return JSON string safe for embedding into templates."""
    return json.dumps(load_project_templates(), cls=DjangoJSONEncoder)


def template_choices() -> List[Tuple[str, str]]:
    return [(str(template.get("id")), str(template.get("name"))) for template in load_project_templates()]


def serialize_template_instance(template) -> Dict[str, Any]:
    """Public helper to serialize a Template ORM instance."""
    return _serialize_template_object(template)
