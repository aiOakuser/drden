"""Structured blueprint data for shareable techpack layouts."""

from __future__ import annotations

from typing import Any, Dict, Optional


def _normalize_slug(value: str) -> str:
    """Normalize incoming slugs so hyphens/underscores resolve to a single key."""
    if not value:
        return ""
    cleaned = value.strip().lower().replace("_", "-")
    return "-".join(part for part in cleaned.split("-") if part)


DESERT_SHADOWS_BLUEPRINT: Dict[str, Any] = {
    "slug": "desert-shadows",
    "hero": {
        "badge": "Pack 02 · Activewear Capsule",
        "icon": "✅",
        "title": "DESERT SHADOWS",
        "subtitle": "Performance Activewear Capsule by AIOAK Athletica",
        "supporting_copy": [
            "Same serif-forward layout system used on the Fuel Fortress sample.",
            "Minimal, high-fashion grid with disciplined spacing and refined typography.",
        ],
    },
    "project_breakdown": {
        "label": "PROJECT BREAKDOWN",
        "kicker": "4-stage roadmap • two-column grid",
    },
    "stages": [
        {
            "title": "Stage 01 / Design & Tech Development",
            "items": [
                "Technical activewear flats",
                "Seamline engineering for mobility",
                "Compression-zoned pattern mapping",
                "Fabric selection: nylon/spandex blends",
                "Color palette: sand, stone, cactus, dusk earth",
                "Print / reflective trim placement",
                "Fit block development (athletic fit)",
                "Vendor + mill catalog review",
            ],
        },
        {
            "title": "Stage 02 / Pre-Production",
            "items": [
                "Fabric swatches + weight testing (220–260gsm)",
                "Stretch recovery / abrasion test results",
                "Bulk fabric shrinkage test",
                "Prototype sample (Round 1)",
                "Pattern development + DXF files",
                "BOM (Bill of Materials) creation",
                "Factory costing + timelines",
                "Fit sample development & approval",
            ],
        },
        {
            "title": "Stage 03 / Production",
            "items": [
                "Pattern grading XS–XXL",
                "Flatlock QC stitching",
                "Reflective trim heat-transfer testing",
                "Size set approval",
                "Bulk cutting (high-yield marker layout)",
                "Final fit round (Round 2)",
                "Bulk sewing + finishing QC",
                "Packaging, labeling, freight coordination",
            ],
        },
        {
            "title": "Stage 04 / Media Direction",
            "items": [
                "Outdoor desert location scouting",
                "Model casting: athletic profiles",
                "Shot list + action storyboard",
                "Product-motion videos",
                "Texture close-ups for website",
                "Social reels + product highlight edits",
            ],
        },
    ],
    "style_sheet": {
        "brand": "AIOAKATHLETICA",
        "title": "Style Sheet — ShadowFlex Jogger (DS-A102)",
        "notes": "Style numbers + fabric details locked for investor-ready deck.",
        "specs": [
            {"label": "Style Code", "value": "DS-A102 / ShadowFlex Jogger"},
            {"label": "Fabric", "value": "78% Nylon / 22% Elastane"},
            {"label": "Weight", "value": "Midweight compression"},
            {"label": "Feature", "value": "Reflective heat-transfer trimming"},
            {"label": "Fit", "value": "Athletic tapered"},
            {"label": "Size Range", "value": "XS–XXL"},
        ],
    },
    "colorways": [
        {"name": "Stone", "hex": "#d8c9b2", "description": "Matte sandstone neutral"},
        {"name": "Taupe", "hex": "#b49982", "description": "Warm dune midtone"},
        {"name": "Deep Earth", "hex": "#5b4130", "description": "Grounding espresso base"},
        {"name": "Cactus Green", "hex": "#4f6b4a", "description": "Desert flora accent"},
        {"name": "Desert Night", "hex": "#1f262f", "description": "After-dark contrast"},
    ],
    "design_sketches": {
        "label": "DESIGN SKETCHES",
        "subtitle": "Layout matching the Fuel Fortress sample",
        "items": [
            "Front view technical sketch",
            "Back view technical sketch",
            "Side seam compression zone diagrams",
            "Pocket construction detail",
            "Reflective trim map",
        ],
    },
    "footer_note": "Generated via Global Designer Hub • Powered by the TekPak layout engine.",
}


TEKPAK_BLUEPRINTS: Dict[str, Dict[str, Any]] = {
    DESERT_SHADOWS_BLUEPRINT["slug"]: DESERT_SHADOWS_BLUEPRINT,
}


def get_techpack_blueprint(slug: str) -> Optional[Dict[str, Any]]:
    """Return a blueprint dictionary for the requested slug, if we have one."""
    key = _normalize_slug(slug)
    if not key:
        return None
    return TEKPAK_BLUEPRINTS.get(key)
