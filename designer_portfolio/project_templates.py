import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Any, Tuple

from django.core.serializers.json import DjangoJSONEncoder


class ProjectTemplateNotFound(Exception):
    """Raised when a requested project template could not be located."""


PROJECT_TEMPLATE_PATH = Path(__file__).resolve().parent / "data" / "project_templates.json"


def _normalize_template(template: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure optional keys exist so downstream rendering logic can rely on them."""
    template.setdefault("summary", [])
    template.setdefault("thumbnail", {})
    template.setdefault("cover", {})
    template.setdefault("stages", [])
    template.setdefault("productSpec", {})
    return template


@lru_cache(maxsize=1)
def load_project_templates() -> List[Dict[str, Any]]:
    """Load and cache the list of project templates from disk."""
    if not PROJECT_TEMPLATE_PATH.exists():
        return []

    with PROJECT_TEMPLATE_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    templates = payload.get("templates", [])
    return [_normalize_template(t) for t in templates]


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
