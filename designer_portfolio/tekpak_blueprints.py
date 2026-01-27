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
        "subtitle": "Performance Activewear Capsule by GlobalDesignerHub Athletica",
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
        "brand": "GLOBALDESIGNERHUB ATHLETICA",
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


FUEL_FORTRESS_AERO_BLUEPRINT: Dict[str, Any] = {
    "slug": "fuel-fortress-aero",
    "hero": {
        "badge": "Pack 01 · Merch Dev Line",
        "icon": "🛡️",
        "title": "FUEL FORTRESS — AERO PROGRAM",
        "subtitle": "Merch Development Line · Presented by Run Volume One",
        "supporting_copy": [
            "Serif-forward typography and burgundy palette directly inspired by the reference deck.",
            "Built for dual Aero hoodies with wrap-around pockets, puff print placements, and Run Volume trims.",
        ],
    },
    "project_breakdown": {
        "label": "PROJECT BREAKDOWN",
        "kicker": "Four-stage workflow · technical hoodies",
    },
    "stages": [
        {
            "title": "Stage 01 / Design & Tech Dev",
            "items": [
                "Technical flats for Aero Hoodie 1 & 2",
                "Style numbers + fabric/color assignment (HAR#-2621 series)",
                "Wrap pocket seam callouts + binding spec",
                "Embroidery map + puff print placement",
                "Contrast hood/cowl fabrication notes",
                "Vendor + trim catalog pulled from Run Volume One",
                "Color map: wine, stone, dune, charcoal, bone",
                "Fit comments + sample measurement targets",
            ],
        },
        {
            "title": "Stage 02 / Pre-Production",
            "items": [
                "Lab dips, hand-feel notes, wash results",
                "Bulk shrinkage test (cotton + brushed fleece)",
                "Pattern development + DXF export for front/back + hood",
                "Pocket opening reinforcement sample",
                "Care/content label copy & placement",
                "BOM with fabric yield + trims",
                "Factory costing + lead time calendar",
                "Fit sample review deck with annotated photos",
            ],
        },
        {
            "title": "Stage 03 / Production",
            "items": [
                "Fabric PO + roll allocation",
                "Marker + cut ticket (wrap pocket placement)",
                "Top sample (#0) approval + requested tweaks",
                "Bulk sewing + reinforcement at wrap pocket seam",
                "Puff print strike-off approval",
                "Bulk QC + spec measurement logging",
                "Packing method (fold, tissue, poly, carton)",
                "Freight docs + duty receipts",
            ],
        },
        {
            "title": "Stage 04 / Media Direction",
            "items": [
                "Studio editorial + concrete rooftop location scout",
                "Model casting: Run Volume athletes + creatives",
                "Shot list referencing original Fuel Fortress layout",
                "Motion clip + BTS capture for reels",
                "Typography + storytelling carousel assets",
                "Lookbook schedule, call sheets, budget",
            ],
        },
    ],
    "style_sheet": {
        "brand": "FUEL FORTRESS",
        "title": "Style Sheet — Aero Hoodie 1 & 2 (HAR#-2621)",
        "notes": "Wrap-around pocket detail, no side seams, high-cowl hood.",
        "specs": [
            {"label": "Style Code", "value": "HAR#-2621 / Aero Hoodie Program"},
            {"label": "Fabric", "value": "380gsm Cotton + Brushed Fleece"},
            {"label": "Lining", "value": "Cotton 40s / 60% Polyester jersey"},
            {"label": "Trim Plan", "value": "Matte puff print + tonal embroidery"},
            {"label": "Fit", "value": "Oversized drop shoulder"},
            {"label": "Size Range", "value": "XXS–XXL"},
        ],
    },
    "colorways": [
        {"name": "Wine Signal", "hex": "#5c1b2b", "description": "Burgundy inspired by the reference deck headline"},
        {"name": "Ice Chalk", "hex": "#ede8e3", "description": "Soft neutral for tonal printing"},
        {"name": "Storm Smoke", "hex": "#4d4c52", "description": "Charcoal base for reflective hits"},
        {"name": "Oat Field", "hex": "#b7a99a", "description": "Warm dune midtone"},
        {"name": "Cinder Black", "hex": "#1f1a1b", "description": "Anchor for typography lockups"},
    ],
    "design_sketches": {
        "label": "DESIGN SCHEMATICS",
        "subtitle": "Hoodie-focused schematics with wrap pocket detail",
        "items": [
            "Front elevation with wrap pocket seam",
            "Back view showcasing oversized hood",
            "Cowl hood pattern overlay",
            "Pocket opening + bartack detail",
            "Typography / puff print placement map",
        ],
    },
    "footer_note": "Generated via Global Designer Hub • Powered by the TekPak layout engine.",
}


FUEL_FORTRESS_OUTPOST_BLUEPRINT: Dict[str, Any] = {
    "slug": "fuel-fortress-outpost",
    "hero": {
        "badge": "Pack 02 · Weather Ops Capsule",
        "icon": "🧭",
        "title": "FUEL FORTRESS — OUTPOST SHELL",
        "subtitle": "Merch Development Line · Run Volume One Field Division",
        "supporting_copy": [
            "Weather-ready outerwear decked with taping, drawcord engineering, and serif typography.",
            "Intended for investor previews showing the complete development trail from concept to media.",
        ],
    },
    "project_breakdown": {
        "label": "PROJECT BREAKDOWN",
        "kicker": "Four-stage build · weatherproof outerwear",
    },
    "stages": [
        {
            "title": "Stage 01 / Design & Tech Dev",
            "items": [
                "Technical flats for storm shell + detachable hood",
                "Style numbers, trim legend, heat-weld callouts",
                "Fabric + membrane sourcing (10k/10k performance)",
                "Embroidery + silicon badge placement",
                "Ventilation panel map + mesh specs",
                "Vendor + factory catalog for seam taping",
                "Color palette stacked around clay, stone, ember",
                "Fit intent: relaxed tactical shell",
            ],
        },
        {
            "title": "Stage 02 / Pre-Production",
            "items": [
                "Lab dips + taped seam compatibility testing",
                "Rain chamber + wind resistance reports",
                "Pattern development with sleeve articulation",
                "Bom + trim BOM (cord stoppers, toggles, zips)",
                "Factory costing + seam tape surcharge",
                "Fit sample comments + arm mobility scoring",
                "Care label copy w/ durable water repellent instructions",
                "Pre-production sample approval with annotated deck",
            ],
        },
        {
            "title": "Stage 03 / Production",
            "items": [
                "Fabric allocation + roll shading plan",
                "Marker + cut map with seam tape allowances",
                "Top of production sample sign-off",
                "Heat-weld QC + seam tape adhesion audits",
                "Bulk sewing + toggle installation QC",
                "Full garment press + packing sequence",
                "Carton labels + HTS coding",
                "Freight booking + insurance docs",
            ],
        },
        {
            "title": "Stage 04 / Media Direction",
            "items": [
                "Foggy forest + rooftop location scout",
                "Model casting (movement testers + hikers)",
                "Shot list showing pocket function + hood stows",
                "Sound design brief for rain ambience",
                "Color-grading deck referencing burgundy headline",
                "Launch cadence across lookbook, reels, product page",
            ],
        },
    ],
    "style_sheet": {
        "brand": "FUEL FORTRESS",
        "title": "Style Sheet — Outpost Weather Shell (FFO-118)",
        "notes": "Triple-layer shell with taped seams + modular hood.",
        "specs": [
            {"label": "Style Code", "value": "FFO-118"},
            {"label": "Fabric", "value": "Nylon 70D + PU membrane"},
            {"label": "Waterproofing", "value": "10K / 10K seam sealed"},
            {"label": "Hardware", "value": "Matte gunmetal toggles + reversed coil zips"},
            {"label": "Fit", "value": "Relaxed tactical shell"},
            {"label": "Size Range", "value": "XS–XXL"},
        ],
    },
    "colorways": [
        {"name": "Clay Barricade", "hex": "#a4593c", "description": "Earthen orange accent seen in the deck photo"},
        {"name": "Pumice", "hex": "#e1d8ce", "description": "Bone neutral for tonal logos"},
        {"name": "Obsidian", "hex": "#1c1a1a", "description": "Deep base color"},
        {"name": "Storm Graphite", "hex": "#4b4d52", "description": "Panels + seam tape"},
        {"name": "Fern Signal", "hex": "#4e6a4a", "description": "Interior mesh pop"},
    ],
    "design_sketches": {
        "label": "DESIGN SCHEMATICS",
        "subtitle": "Outerwear body + venting studies",
        "items": [
            "Front elevation with chest pocket taping",
            "Back view with vent + hood stow detail",
            "Sleeve articulation overlay",
            "Hem drawcord + toggle detail",
            "Storm flap construction callout",
        ],
    },
    "footer_note": "Generated via Global Designer Hub • Powered by the TekPak layout engine.",
}


FUEL_FORTRESS_RALLY_BLUEPRINT: Dict[str, Any] = {
    "slug": "fuel-fortress-rally",
    "hero": {
        "badge": "Pack 03 · Track Capsule",
        "icon": "🏁",
        "title": "FUEL FORTRESS — RALLY PACK",
        "subtitle": "Motorsport-leaning merch program · Run Volume One Studio",
        "supporting_copy": [
            "Mirrors the serif-led Fuel Fortress deck but injects racing stripes, perforated panels, and sponsor callouts.",
            "Creates a motion-ready presentation for nylon zip-ups, pit-stop pants, and utility tees.",
        ],
    },
    "project_breakdown": {
        "label": "PROJECT BREAKDOWN",
        "kicker": "Four-stage sequencing · track uniform set",
    },
    "stages": [
        {
            "title": "Stage 01 / Design & Tech Dev",
            "items": [
                "Technical flats for pit zip jacket + rally pant",
                "Style codes + sponsor placement plan",
                "Fabric board: ripstop nylon, spacer mesh, rib",
                "Color blocking map (crimson / charcoal / bone)",
                "Reflective piping + embroidery notes",
                "Measurement spec for articulated knee",
                "Vendor catalog for perforated panels",
                "Graphic lockup & typography spec (Playfair headline)",
            ],
        },
        {
            "title": "Stage 02 / Pre-Production",
            "items": [
                "Lab dips + reflective trim testing",
                "Pattern revisions for curved side seam",
                "BOM + trim matrix (piping, zips, snaps)",
                "Proto sample (round 1) + fit comments",
                "In-house wear test at simulated pit stop",
                "Care label translations + compliance",
                "Factory costing + delivery calendar",
                "PP sample approval (photos + callouts)",
            ],
        },
        {
            "title": "Stage 03 / Production",
            "items": [
                "Fabric QC + color shade grouping",
                "Marker layout with stripe blocking",
                "Top of production sign-off",
                "Bulk sewing + reflective piping QC",
                "Heat transfer sponsor hits (strike-off)",
                "Spec measurement + grading audit",
                "Packing fold w/ jersey bag inclusion",
                "Bill of lading + customs packet",
            ],
        },
        {
            "title": "Stage 04 / Media Direction",
            "items": [
                "Night-track location + smoke machine brief",
                "Talent casting: drivers + pit crew stylists",
                "Shot list with motion blur + hero stills",
                "Storyboard for reels + hero edit",
                "Audio brief (engine layers + Vogue type clicks)",
                "Merch drop calendar + rollout copy bank",
            ],
        },
    ],
    "style_sheet": {
        "brand": "FUEL FORTRESS",
        "title": "Style Sheet — Rally Zip Jacket (FFR-207)",
        "notes": "Nylon ripstop body, reflective piping, articulated sleeves.",
        "specs": [
            {"label": "Style Code", "value": "FFR-207"},
            {"label": "Fabric", "value": "120gsm Nylon Ripstop + Spacer Mesh"},
            {"label": "Feature", "value": "Reflective piping & sponsor transfers"},
            {"label": "Fit", "value": "Relaxed track silhouette"},
            {"label": "Closure", "value": "Two-way VISLON zip"},
            {"label": "Size Range", "value": "XS–3XL"},
        ],
    },
    "colorways": [
        {"name": "Crimson Apex", "hex": "#6b1f2a", "description": "Matches the Fuel Fortress masthead tone"},
        {"name": "Grid Grey", "hex": "#5a5c60", "description": "Racing stripe + panel filler"},
        {"name": "Ivory Flag", "hex": "#efe8df", "description": "Ground for typography hits"},
        {"name": "Char Black", "hex": "#1b191b", "description": "Base for sponsor placements"},
    ],
    "design_sketches": {
        "label": "DESIGN SCHEMATICS",
        "subtitle": "Track jacket + pant callouts",
        "items": [
            "Front jacket with stripe blocking",
            "Back view showing sponsor zone",
            "Pant articulation + knee dart diagram",
            "Pocket opening + zipper guard detail",
            "Badge + embroidery layout",
        ],
    },
    "footer_note": "Generated via Global Designer Hub • Powered by the TekPak layout engine.",
}


FUEL_FORTRESS_SIGNAL_BLUEPRINT: Dict[str, Any] = {
    "slug": "fuel-fortress-signal",
    "hero": {
        "badge": "Pack 04 · Reflective Capsule",
        "icon": "📡",
        "title": "FUEL FORTRESS — SIGNAL KIT",
        "subtitle": "Night ops merch program · Run Volume One Media",
        "supporting_copy": [
            "Extends the Fuel Fortress visual language to a reflective capsule with glowing trims.",
            "Pairs serif headlines with futuristic annotations for a persuasive investor-ready pack.",
        ],
    },
    "project_breakdown": {
        "label": "PROJECT BREAKDOWN",
        "kicker": "Four-stage sequencing · reflective fleece + shell",
    },
    "stages": [
        {
            "title": "Stage 01 / Design & Tech Dev",
            "items": [
                "Technical flats for reflective fleece + hybrid anorak",
                "Fabric sourcing: brushed fleece + reflective ripstop",
                "Style numbers + numbering logic for SKUs",
                "Heat-transfer + glow ink placement map",
                "Trim legend (zip pulls, cords, reflective thread)",
                "Vendor catalog cross-check for night visibility",
                "Color mapping (infrared, asphalt, fog, onyx)",
                "Fit + measurement spec for layering",
            ],
        },
        {
            "title": "Stage 02 / Pre-Production",
            "items": [
                "Glow ink + reflective testing (ANSI compliance)",
                "Prototype sample photo review under low light",
                "Pattern adjustments for hidden venting",
                "BOM + trim BOM with reflective price tiers",
                "Factory costing + schedule with night QA slots",
                "Care label instructions for light-sensitive inks",
                "PP sample with annotated GIF/video references",
                "Bulk order forecast + carton quantity plan",
            ],
        },
        {
            "title": "Stage 03 / Production",
            "items": [
                "Material QC under multiple lighting temps",
                "Marker layout to orient reflective grain",
                "Top of production approval (night + day photos)",
                "Bulk sewing + seam sealing for reflective panels",
                "Heat transfer strike-off + adhesion testing",
                "Spec measurement + reflection lux report",
                "Packing list w/ black tissue + branded desiccant",
                "Freight + arrival inspection booking",
            ],
        },
        {
            "title": "Stage 04 / Media Direction",
            "items": [
                "Night city roof + tunnel location scout",
                "Casting with dancers / runners for light trails",
                "Shot list mixing long exposure + macro details",
                "Storyboard for reel with glitch typography",
                "Lighting plan (RGB tubes + warm spill)",
                "Deliverables: hero film, IG carousel, product GIFs",
            ],
        },
    ],
    "style_sheet": {
        "brand": "FUEL FORTRESS",
        "title": "Style Sheet — Signal Hybrid Anorak (FFS-314)",
        "notes": "Reflective ripstop shell with brushed fleece lining.",
        "specs": [
            {"label": "Style Code", "value": "FFS-314"},
            {"label": "Fabric", "value": "Reflective Nylon Ripstop + 320gsm Fleece"},
            {"label": "Feature", "value": "Glow ink logos + reflective piping"},
            {"label": "Fit", "value": "Boxy anorak, drop shoulder"},
            {"label": "Hardware", "value": "Matte black toggles + waterproof zip"},
            {"label": "Size Range", "value": "XS–XXL"},
        ],
    },
    "colorways": [
        {"name": "Infrared Pulse", "hex": "#a82832", "description": "Matches the Fuel Fortress masthead hue"},
        {"name": "Fog Concrete", "hex": "#d6d2cc", "description": "Soft neutral for tonal base"},
        {"name": "Asphalt", "hex": "#3c3c43", "description": "Body fabric for reflective contrast"},
        {"name": "Night Signal", "hex": "#0d0d11", "description": "Deep black for piping + cuffs"},
        {"name": "Static Silver", "hex": "#b5bcc4", "description": "Reflective trim accent"},
    ],
    "design_sketches": {
        "label": "DESIGN SCHEMATICS",
        "subtitle": "Reflective placement + venting studies",
        "items": [
            "Front view with reflective sweep",
            "Back view showing glow print arcs",
            "Venting detail + mesh overlay",
            "Pocket + zipper detail callouts",
            "Lighting cue reference diagrams",
        ],
    },
    "footer_note": "Generated via Global Designer Hub • Powered by the TekPak layout engine.",
}


FUEL_FORTRESS_MONOLITH_BLUEPRINT: Dict[str, Any] = {
    "slug": "fuel-fortress-monolith",
    "hero": {
        "badge": "Pack 05 · Minimal Capsule",
        "icon": "🧱",
        "title": "FUEL FORTRESS — MONOLITH SET",
        "subtitle": "Minimalist capsule · Run Volume One Atelier",
        "supporting_copy": [
            "Extends the Fuel Fortress serif layout into a tonal, almost architectural presentation.",
            "Good for tonal sweatsuits, laser-etched graphics, and gallery-style lookbooks.",
        ],
    },
    "project_breakdown": {
        "label": "PROJECT BREAKDOWN",
        "kicker": "Four-stage sequencing · tonal sweatsuit capsule",
    },
    "stages": [
        {
            "title": "Stage 01 / Design & Tech Dev",
            "items": [
                "Technical flats for crew, sweatpant, poncho topper",
                "Fabric palette: 420gsm cotton loopback + jersey",
                "Emboss / laser etching placement plan",
                "Branding map (micro serif logos + blind deboss)",
                "Color stack (fossil, bone, shale, ink)",
                "Vendor catalog + mill references for high GSM fleece",
                "Fit block creation for cropped + oversized silhouettes",
                "Measurement tables, POM callouts, ease notes",
            ],
        },
        {
            "title": "Stage 02 / Pre-Production",
            "items": [
                "Lab dips + tonal embroidery tests",
                "Fabric compression + shrink testing",
                "Pattern adjustments for side panel articulation",
                "BOM covering trims, woven labels, hangtags",
                "Factory costing + MOQ negotiation",
                "Sample review with tactile swatch cards",
                "Care/content label translations",
                "Spec comment deck returned to vendor",
            ],
        },
        {
            "title": "Stage 03 / Production",
            "items": [
                "Bulk fabric booking + shade grouping",
                "Marker making with self rib cuffs",
                "Top sample approval (Stage 0 of production)",
                "Bulk sewing + panel pressing QC",
                "Emboss / laser process verification",
                "Spec measurement + grading audit",
                "Packing with muslin dust bag + recycled poly",
                "Freight + inbound QA scheduling",
            ],
        },
        {
            "title": "Stage 04 / Media Direction",
            "items": [
                "Gallery space location scout",
                "Casting brief (contemporary dancers + sculptural poses)",
                "Shot list (macro fabric shots, architecture angles)",
                "Lighting plan: soft key with burgundy accent gels",
                "Soundtrack brief (ambient + industrial)",
                "Launch checklist (press kit, lookbook, product page)",
            ],
        },
    ],
    "style_sheet": {
        "brand": "FUEL FORTRESS",
        "title": "Style Sheet — Monolith Crew (FFM-411)",
        "notes": "Ultra-heavy loopback fleece with blind deboss logo.",
        "specs": [
            {"label": "Style Code", "value": "FFM-411"},
            {"label": "Fabric", "value": "420gsm Loopback Cotton"},
            {"label": "Finishing", "value": "Silicone wash + enzyme softener"},
            {"label": "Trim Plan", "value": "Blind deboss + tonal satin label"},
            {"label": "Fit", "value": "Cropped body, wide sleeve"},
            {"label": "Size Range", "value": "XXS–XXL"},
        ],
    },
    "colorways": [
        {"name": "Fossil", "hex": "#9f9486", "description": "Warm stone base"},
        {"name": "Bone Canvas", "hex": "#ede4da", "description": "Light tonal highlight"},
        {"name": "Shale", "hex": "#6e6b64", "description": "Mid grey for sets"},
        {"name": "Ink Well", "hex": "#1f1e21", "description": "Deep accent for typography"},
    ],
    "design_sketches": {
        "label": "DESIGN SCHEMATICS",
        "subtitle": "Minimal monochrome sketches",
        "items": [
            "Crew front/back with deboss callouts",
            "Sweatpant with dart placement",
            "Poncho silhouette with hood",
            "Logo placement + tonal embroidery",
            "Fabric cross-section reference",
        ],
    },
    "footer_note": "Generated via Global Designer Hub • Powered by the TekPak layout engine.",
}


_BLUEPRINT_REGISTRY = [
    DESERT_SHADOWS_BLUEPRINT,
    FUEL_FORTRESS_AERO_BLUEPRINT,
    FUEL_FORTRESS_OUTPOST_BLUEPRINT,
    FUEL_FORTRESS_RALLY_BLUEPRINT,
    FUEL_FORTRESS_SIGNAL_BLUEPRINT,
    FUEL_FORTRESS_MONOLITH_BLUEPRINT,
]

TEKPAK_BLUEPRINTS: Dict[str, Dict[str, Any]] = {entry["slug"]: entry for entry in _BLUEPRINT_REGISTRY}


def get_techpack_blueprint(slug: str) -> Optional[Dict[str, Any]]:
    """Return a blueprint dictionary for the requested slug, if we have one."""
    key = _normalize_slug(slug)
    if not key:
        return None
    return TEKPAK_BLUEPRINTS.get(key)
