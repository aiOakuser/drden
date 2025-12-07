import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from ...models import Template, TemplateStage, TemplateProductBlock
from ...project_templates import PROJECT_TEMPLATE_PATH


def _coerce_stage_items(stage_data: Dict[str, Any]) -> List[str]:
    for key in ("defaultItems", "defaultBullets", "items"):
        items = stage_data.get(key)
        if isinstance(items, list):
            return [str(item).strip() for item in items if str(item).strip()]
    return []


def _normalize_product_blocks(template_data: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    blocks = template_data.get("productBlocks")
    if isinstance(blocks, list) and blocks:
        return blocks

    product_spec = template_data.get("productSpec")
    if isinstance(product_spec, dict) and product_spec:
        fallback_block = {
            "id": f"{template_data.get('id')}_spec",
            "label": template_data.get("name") or template_data.get("id") or "Product",
            "titlePlaceholder": product_spec.get("title") or "Product Spec",
            "codePlaceholder": product_spec.get("code") or "",
            "defaultViews": product_spec.get("defaultViews") or ["FRONT", "BACK"],
            "detailsTemplate": {
                "fields": product_spec.get("fields") or [],
            },
        }
        return [fallback_block]

    return []


class Command(BaseCommand):
    help = "Load project templates from a JSON file into the Template tables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--path",
            type=str,
            default=str(PROJECT_TEMPLATE_PATH),
            help="Path to the template JSON file. Defaults to designer_portfolio/data/project_templates.json",
        )
        parser.add_argument(
            "--template-id",
            dest="template_id",
            type=str,
            help="Optional template id to import. If omitted, imports every template in the file.",
        )
        parser.add_argument(
            "--truncate",
            action="store_true",
            help="Delete existing templates before importing.",
        )

    def handle(self, *args, **options):
        path = Path(options["path"]).expanduser()
        template_id_filter = (options.get("template_id") or "").strip()
        truncate = bool(options.get("truncate", False))

        if not path.exists():
            raise CommandError(f"Template file '{path}' does not exist.")

        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        templates = payload.get("templates") or []
        if template_id_filter:
            templates = [item for item in templates if item.get("id") == template_id_filter]
            if not templates:
                raise CommandError(f"Template '{template_id_filter}' not found in {path}.")

        if not templates:
            self.stdout.write(self.style.WARNING("No templates to import."))
            return

        with transaction.atomic():
            if truncate:
                Template.objects.all().delete()

            for template_data in templates:
                self._import_template(template_data)

        self.stdout.write(self.style.SUCCESS(f"Imported {len(templates)} template(s) from {path}"))

    def _import_template(self, template_data: Dict[str, Any]) -> None:
        template_id = template_data.get("id")
        if not template_id:
            raise CommandError("Every template must include an 'id' field.")

        template_defaults = {
            "name": template_data.get("name") or template_id,
            "layout_key": template_data.get("layoutKey") or "",
            "cover_title_placeholder": template_data.get("cover", {}).get("titlePlaceholder") or template_data.get("name") or template_id,
            "cover_subtitle_placeholder": template_data.get("cover", {}).get("subtitlePlaceholder")
            or template_data.get("cover", {}).get("subtitle")
            or "",
            "summary": template_data.get("summary") or [],
            "metadata": {
                "category": template_data.get("category", ""),
                "thumbnail": template_data.get("thumbnail", {}),
                "cover": template_data.get("cover", {}),
            },
        }

        template, _ = Template.objects.update_or_create(
            id=template_id,
            defaults=template_defaults,
        )

        template.stages.all().delete()
        stage_entries = template_data.get("stages") or []
        for index, stage_data in enumerate(stage_entries, start=1):
            TemplateStage.objects.create(
                template=template,
                stage_index=stage_data.get("stageNumber") or stage_data.get("stage_index") or index,
                title=stage_data.get("title") or f"Stage {index}",
                default_items=_coerce_stage_items(stage_data),
                layout_hint=stage_data.get("layoutHint", ""),
            )

        template.product_blocks.all().delete()
        for index, block_data in enumerate(_normalize_product_blocks(template_data), start=1):
            TemplateProductBlock.objects.create(
                template=template,
                block_index=block_data.get("block_index") or block_data.get("blockIndex") or index,
                label=block_data.get("label") or template_defaults["name"],
                title_placeholder=block_data.get("titlePlaceholder") or block_data.get("title") or template_defaults["name"],
                code_placeholder=block_data.get("codePlaceholder") or block_data.get("code") or "",
                default_views=block_data.get("defaultViews") or [],
                details_schema=block_data.get("detailsTemplate") or block_data.get("details_schema") or {},
            )
