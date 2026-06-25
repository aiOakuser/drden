import base64
import copy
import json
import logging
import os
import re
import urllib.request
import uuid
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone as dt_timezone
from pathlib import Path
from urllib.error import HTTPError, URLError

from django.shortcuts import render, redirect, get_object_or_404, resolve_url
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.views.generic import TemplateView, DetailView, ListView, CreateView, FormView
from django.contrib.auth.views import LoginView, PasswordResetView, PasswordResetConfirmView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login, authenticate, get_user_model
from django.http import JsonResponse, Http404, QueryDict, HttpResponse
from django.views.decorators.csrf import requires_csrf_token, csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.mail import EmailMessage, BadHeaderError
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator, validate_email
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.db import transaction, IntegrityError
from django.db.utils import OperationalError, ProgrammingError
from django.db.models import Q, Count, F, Prefetch
from django.urls import reverse_lazy, reverse, NoReverseMatch
from django.utils.text import slugify
from django.core.paginator import Paginator
from django.templatetags.static import static
from urllib.parse import urlencode
from .forms import (
    DesignerSignUpForm,
    DesignerLoginForm,
    DesignerPasswordResetForm,
    ReportProblemForm,
    ContactForm,
    StudentInviteRequestForm,
    ProjectCreateForm,
    EventAttendeeForm,
    EventCollaborationForm,
    NewOrderAccessForm,
)
from .auth_utils import ensure_designer_access
from .recaptcha_utils import recaptcha_template_context, verify_recaptcha_token
from .context_processors import _google_oauth_ready
from .messenger_utils import user_can_use_messenger, message_contains_prohibited_content
from .emails import (
    send_registration_notifications,
    notify_user_password_reset_completion,
    notify_problem_report,
    notify_designer_new_dress_order,
    notify_viewer_dress_order_confirmation,
)
from .models import (
    DesignerProfile,
    DressOrder,
    DressOrderUpdate,
    SubscriptionPlan,
    UserSubscription,
    Design,
    DesignImage,
    Collection,
    Event,
    WebAuthnCredential,
    DesignerAISession,
    DesignerAIMessage,
    ChatConversation,
    ChatMessage,
    DocPage,
    ForumCategory,
    ForumTopic,
    ForumPost,
    ForumLike,
    ForumBookmark,
    ForumNotification,
    ForumUserProfile,
    ProblemReport,
    Template,
    Project,
    ProjectStage,
    ProjectStageBullet,
    ProjectProductSpec,
    ProjectProductSpecField,
)
from .constants import REGIONAL_HIRING_AREAS
from .project_templates import load_project_templates, serialize_templates_for_client
from .tekpak_blueprints import get_techpack_blueprint
from .serializers import EventSerializer

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticationCredential,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialUserEntity,
    RegistrationCredential,
    UserVerificationRequirement,
)


logger = logging.getLogger(__name__)

RUNWAY_GUEST_LINK_EXPIRY_DAYS = 7
RUNWAY_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".avi"}
RUNWAY_COLLECTION_CAPABILITIES = [
    {
        "title": "Runway-ready lookbooks",
        "description": "Versioned lookbooks with cover imagery, look numbers, and capsule notes keep every drop documented.",
        "icon": "fa-solid fa-book-open",
        "tagline": "Versioned lookbooks + cover imagery",
    },
    {
        "title": "Motion & tech pack attachments",
        "description": "Drop in motion references alongside PDF or XLS tech packs so factories receive everything in one link.",
        "icon": "fa-solid fa-film",
        "tagline": "Lookbooks, motion, and tech packs",
    },
    {
        "title": "Private review & embeds",
        "description": "Share a private review link or embed the same collection across your site without duplicating uploads.",
        "icon": "fa-solid fa-share-nodes",
        "tagline": "Share private review links or embed",
    },
    {
        "title": "Auto-expiring guest access",
        "description": (
            f"Guest links expire automatically after {RUNWAY_GUEST_LINK_EXPIRY_DAYS} days, keeping review threads secure "
            "while still being effortless for partners."
        ),
        "icon": "fa-solid fa-shield",
        "tagline": "Guest links expire automatically",
    },
]

PROJECT_TEMPLATE_DEFAULT_SUMMARY = [
    "Includes four stages + single product spec page",
]


VOLUMEONE_INSTAGRAM_USERNAME = "runvolumeone"
VOLUMEONE_INSTAGRAM_APP_ID = "936619743392459"


def _gdh_instagram_profile_url() -> str:
    """Canonical GDH Instagram link (settings.GDH_INSTAGRAM_URL)."""
    return (getattr(settings, "GDH_INSTAGRAM_URL", None) or "").strip()
VOLUMEONE_FEED_CACHE_KEY = "designer_portfolio:volumeone-feed"
VOLUMEONE_FEED_CACHE_TTL = 60 * 30  # 30 minutes
VOLUMEONE_MAX_SLIDES = 20
VOLUMEONE_DEFAULT_SLIDES = 8
VOLUMEONE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

VOLUMEONE_FALLBACK_PROFILE = {
    "handle": "runvolumeone",
    "name": "RUNWAY",
    "biography": "Design House",
    "followers": 895,
    "following": 6,
    "posts": 22,
    "avatar_url": (
        "https://scontent-iad3-2.cdninstagram.com/v/t51.2885-19/581897756_17922125034192197_"
        "4135739670115190840_n.jpg?stp=dst-jpg_s320x320_tt6&efg=eyJ2ZW5jb2RlX3RhZyI6InByb2ZpbGVf"
        "cGljLmRqYW5nby4xMDgwLmMyIn0&_nc_ht=scontent-iad3-2.cdninstagram.com&_nc_cat=105&_nc_oc="
        "Q6cZ2QGmFgpA4VJsmOi_dBmZem9ZEcg66BSttejjnpJn8oKOY7DtxPnDNcz58XBKmyFJl8k&_nc_ohc="
        "7yNlwzqGStYQ7kNvwEFNxoA&_nc_gid=KmbyDeXyeGNNQjIipsJhfg&edm=AOQ1c0wBAAAA&ccb=7-5&oh="
        "00_AfiZ40InChy4Ge3SShAxKq6JYb4pvzjN3jxlYVJHGXjobQ&oe=6932D66C&_nc_sid=8b3546"
    ),
}

VOLUMEONE_FALLBACK_SLIDES = [
    {
        "shortcode": "DRIH_xLgex5",
        "image_url": (
            "https://scontent-iad3-2.cdninstagram.com/v/t51.2885-15/583100306_864388666011821_"
            "8294748503970614309_n.jpg?stp=dst-jpg_e15_tt6&_nc_ht=scontent-iad3-2.cdninstagram.com&_nc_cat=105&_nc_oc="
            "Q6cZ2QGCT1VVVUQrA7mi6UEMWfTqtHK-XleOxwKy1cgUeQ3A0cqgJdqNU8Y6k34W4Vwi69Q&_nc_ohc=EkUDmdG73JMQ7kNvwGzwOp9&_"
            "nc_gid=0g-Fhf5Kap5ntbSZ56-HDA&edm=AOQ1c0wBAAAA&ccb=7-5&oh=00_AfjYEhksyOocfS0LdJYnlFl5c6tomkDXa2Wi8sPgmvWg9Q"
            "&oe=6932D6C8&_nc_sid=8b3546"
        ),
        "caption": (
            "see you soon honolulu we are super excited to announce our final stages of prep for our teams first "
            "collective marathon. if you are running honolulu make sure to join our team: runvolumeone"
        ),
        "timestamp": 1763316944,
        "like_count": 38,
        "comment_count": 9,
        "is_video": True,
    },
    {
        "shortcode": "DL07da1P3LP",
        "image_url": (
            "https://scontent-iad3-2.cdninstagram.com/v/t51.2885-15/563727218_18029975375721731_"
            "6557020613612464348_n.jpg?stp=dst-jpg_e35_p1080x1080_sh0.08_tt6&_nc_ht=scontent-iad3-2.cdninstagram.com&_nc_cat="
            "111&_nc_oc=Q6cZ2QGCT1VVVUQrA7mi6UEMWfTqtHK-XleOxwKy1cgUeQ3A0cqgJdqNU8Y6k34W4Vwi69Q&_nc_ohc=Vz9e2VgesIoQ7kNv"
            "wHoywLt&_nc_gid=0g-Fhf5Kap5ntbSZ56-HDA&edm=AOQ1c0wBAAAA&ccb=7-5&oh=00_AfgPAc2cp4a7VAj_gR55J5T1vmhtC1dVvSQKSUY"
            "3TZ2x6A&oe=6932DCEB&_nc_sid=8b3546"
        ),
        "caption": (
            "recap of our recent pop-up with @runvolumeone huge thank you to everyone who pulled up and showed love. "
            "energy was unreal. the community keeps growing and we are just getting started"
        ),
        "timestamp": 1751935686,
        "like_count": 181,
        "comment_count": 54,
        "is_video": True,
    },
    {
        "shortcode": "DLsnl5xS3pJ",
        "image_url": (
            "https://scontent-iad3-2.cdninstagram.com/v/t51.2885-15/582772375_17922124740192197_"
            "6550530905529303132_n.jpg?stp=dst-jpg_e15_tt6&_nc_ht=scontent-iad3-2.cdninstagram.com&_nc_cat=105&_nc_oc="
            "Q6cZ2QGCT1VVVUQrA7mi6UEMWfTqtHK-XleOxwKy1cgUeQ3A0cqgJdqNU8Y6k34W4Vwi69Q&_nc_ohc=mGWbwNfF68oQ7kNvwFWHkFR&_"
            "nc_gid=0g-Fhf5Kap5ntbSZ56-HDA&edm=AOQ1c0wBAAAA&ccb=7-5&oh=00_AfgBg63L_ZdDjITNJF98U1TbidFUS73pao4oZc45PxgEbg&"
            "oe=6932C946&_nc_sid=8b3546"
        ),
        "caption": (
            "thank you. shot and edited by @copyzay designs by @copyzay and @manyamarri brands: @oasis.zm "
            "@outlier.0001 @renovate.clo"
        ),
        "timestamp": 1751656718,
        "like_count": 94,
        "comment_count": 15,
        "is_video": True,
    },
    {
        "shortcode": "DLXzY0QSvvd",
        "image_url": (
            "https://scontent-iad3-1.cdninstagram.com/v/t51.2885-15/504490361_1167534535062625_"
            "5724248030847994982_n.jpg?stp=dst-jpg_e15_tt6&_nc_ht=scontent-iad3-1.cdninstagram.com&_nc_cat=101&_nc_oc="
            "Q6cZ2QGCT1VVVUQrA7mi6UEMWfTqtHK-XleOxwKy1cgUeQ3A0cqgJdqNU8Y6k34W4Vwi69Q&_nc_ohc=ygeC9oaBT3kQ7kNvwGzSlli&_"
            "nc_gid=0g-Fhf5Kap5ntbSZ56-HDA&edm=AOQ1c0wBAAAA&ccb=7-5&oh=00_AfhtPz3oHpqTX-4gOFi8cXuqsXCX9HIQf9dctZJJb7jSKQ&"
            "oe=6932CC2E&_nc_sid=8b3546"
        ),
        "caption": "",
        "timestamp": 1750957971,
        "like_count": 29,
        "comment_count": 7,
        "is_video": True,
    },
    {
        "shortcode": "DLVOqclpPeJ",
        "image_url": (
            "https://scontent-iad3-2.cdninstagram.com/v/t51.2885-15/510961325_17905520445192197_"
            "8408534836598788128_n.jpg?stp=dst-jpg_e35_p1080x1080_sh0.08_tt6&_nc_ht=scontent-iad3-2.cdninstagram.com&_nc_cat="
            "105&_nc_oc=Q6cZ2QGCT1VVVUQrA7mi6UEMWfTqtHK-XleOxwKy1cgUeQ3A0cqgJdqNU8Y6k34W4Vwi69Q&_nc_ohc=b-BCm6smbIMQ7kNv"
            "wFaacf_&_nc_gid=0g-Fhf5Kap5ntbSZ56-HDA&edm=AOQ1c0wBAAAA&ccb=7-5&oh=00_AfiHWYqaErNOEpuf-QMljNCVu7CUl9Qmuwr1kvM_5"
            "G-nJQ&oe=6932D29D&_nc_sid=8b3546"
        ),
        "caption": "2 days out rsvp in bio",
        "timestamp": 1750871533,
        "like_count": 18,
        "comment_count": 3,
        "is_video": False,
    },
    {
        "shortcode": "DLDTcQQoMMw",
        "image_url": (
            "https://scontent-iad3-2.cdninstagram.com/v/t51.2885-15/511533399_18015983099721731_"
            "3685769038166561750_n.jpg?stp=dst-jpg_e35_p1080x1080_sh0.08_tt6&_nc_ht=scontent-iad3-2.cdninstagram.com&_nc_cat="
            "111&_nc_oc=Q6cZ2QGCT1VVVUQrA7mi6UEMWfTqtHK-XleOxwKy1cgUeQ3A0cqgJdqNU8Y6k34W4Vwi69Q&_nc_ohc=YZBpjDxEjckQ7kNvwHzdfzg&_"
            "nc_gid=0g-Fhf5Kap5ntbSZ56-HDA&edm=AOQ1c0wBAAAA&ccb=7-5&oh=00_AfgkZtFJbqhi1t8BGuEmIYhyaWmZJHJC5JhauQO6jpVSIA&oe=6932D724&_nc_sid=8b3546"
        ),
        "caption": (
            "we teamed up with @runvolumeone for our first ever run club appreciate everyone who came out and put in "
            "the early morning work with us"
        ),
        "timestamp": 1750270651,
        "like_count": 98,
        "comment_count": 17,
        "is_video": True,
    },
]


VOLUMEONE_DESIGN_PACK_SLUGS = (
    "desert-shadows",
    "fuel-fortress-aero",
    "fuel-fortress-outpost",
    "fuel-fortress-rally",
    "fuel-fortress-signal",
    "fuel-fortress-monolith",
)


def _build_template_library(entries: list[dict]) -> list[dict]:
    templates: list[dict] = []
    for entry in entries:
        definition = entry["definition"]
        product_blocks = definition.get("productBlocks") or []
        primary_block = product_blocks[0] if product_blocks else {}
        templates.append(
            {
                "id": definition.get("id", ""),
                "name": definition.get("name", ""),
                "summary": entry.get("summary", ""),
                "layout": definition.get("layoutKey", ""),
                "stage_count": len(definition.get("stages") or []),
                "product_block_count": len(product_blocks),
                "primary_views": ", ".join(primary_block.get("defaultViews", [])),
                "primary_block_title": primary_block.get("titlePlaceholder", ""),
                "primary_block_label": primary_block.get("label", ""),
                "code_placeholder": primary_block.get("codePlaceholder", ""),
                "json": json.dumps(definition, indent=2, ensure_ascii=False),
            }
        )
    return templates


_STREET_CIRCUIT_TEMPLATE = {
    "id": "street_circuit",
    "name": "Street Circuit Project Breakdown",
    "layoutKey": "fuel_fortress",
    "cover": {
        "titlePlaceholder": "STREET CIRCUIT",
        "subtitlePlaceholder": "MERCH DEVELOPMENT LINE PRESENTED BY RUN VOLUME ONE",
    },
    "stages": [
        {
            "id": "s1",
            "title": "STAGE 01 / DESIGN & TECH DEV.",
            "defaultItems": [
                "Concept boards & reference pulls",
                "Technical flats / line art",
                "Style number creation & naming",
                "Fabric & trim sourcing shortlist",
                "Graphics / logo lockup exploration",
            ],
        },
        {
            "id": "s2",
            "title": "STAGE 02 / PRE-PRODUCTION",
            "defaultItems": [
                "Fabric yardage cards & lab dips",
                "Shrink / wash testing",
                "Pattern draft & graded size set",
                "Tech pack v1 (measurements + BOM)",
                "Fit sample request to factory",
            ],
        },
        {
            "id": "s3",
            "title": "STAGE 03 / PRODUCTION",
            "defaultItems": [
                "Fit sample try-on & notes",
                "Pattern revision & spec update",
                "TOP sample request & approval",
                "Bulk PO confirmation & timeline",
                "Final bulk QC checklist",
            ],
        },
        {
            "id": "s4",
            "title": "STAGE 04 / MEDIA DIRECTION",
            "defaultItems": [
                "Shoot brief & reference deck",
                "Location + model casting",
                "Shot list / storyboard layout",
                "Launch calendar & asset delivery",
            ],
        },
    ],
    "productBlocks": [
        {
            "id": "pb1",
            "label": "RUNVOLUMEONE",
            "titlePlaceholder": "STREET CIRCUIT ANORAK",
            "codePlaceholder": "[CODE: SC-4401]",
            "defaultViews": ["FRONT", "BACK", "DETAIL"],
            "detailsTemplate": {
                "fields": [
                    {"key": "styleNumber", "label": "Style #"},
                    {"key": "description", "label": "Description"},
                    {"key": "fabricShell", "label": "Fabric (Shell)"},
                    {"key": "fabricContent", "label": "Fabric Content"},
                    {"key": "sizeRange", "label": "Size Range"},
                    {"key": "colorways", "label": "Colorways"},
                ]
            },
        }
    ],
}


_MIDNIGHT_RELAY_TEMPLATE = {
    "id": "midnight_relay",
    "name": "Midnight Relay Night Run Capsule",
    "layoutKey": "fuel_fortress",
    "cover": {
        "titlePlaceholder": "MIDNIGHT RELAY",
        "subtitlePlaceholder": "NIGHT RUN CAPSULE PRESENTED BY RUN VOLUME ONE",
    },
    "stages": [
        {
            "id": "s1",
            "title": "STAGE 01 / DESIGN & TECH DEV.",
            "defaultItems": [
                "Night-run theme & silhouette selection",
                "Reflectivity map & safety requirements",
                "Tech sketches: top, bottom, outerwear",
                "Material callouts: reflective, mesh, jersey",
            ],
        },
        {
            "id": "s2",
            "title": "STAGE 02 / PRE-PRODUCTION",
            "defaultItems": [
                "Vendor outreach for reflective trims",
                "Lab tests: visibility & wash fastness",
                "Pattern build & seam placement review",
                "First proto sample order & costing targets",
            ],
        },
        {
            "id": "s3",
            "title": "STAGE 03 / PRODUCTION",
            "defaultItems": [
                "Proto fit session & feedback",
                "Grading & spec lock",
                "Pre-production samples (PPS) approval",
                "Bulk fabric & trim booking",
            ],
        },
        {
            "id": "s4",
            "title": "STAGE 04 / MEDIA DIRECTION",
            "defaultItems": [
                "Night city location scout",
                "Motion blur / long-exposure test shots",
                "Social teaser plan",
                "Product feature video outline",
            ],
        },
    ],
    "productBlocks": [
        {
            "id": "pb1",
            "label": "RUNVOLUMEONE",
            "titlePlaceholder": "MIDNIGHT RELAY SHELL PANT",
            "codePlaceholder": "[CODE: MR-2212]",
            "defaultViews": ["FRONT", "BACK", "SIDE"],
            "detailsTemplate": {
                "fields": [
                    {"key": "styleNumber", "label": "Style #"},
                    {"key": "description", "label": "Description"},
                    {"key": "fabricShell", "label": "Fabric (Shell)"},
                    {"key": "fabricContent", "label": "Fabric Content"},
                    {"key": "sizeRange", "label": "Size Range"},
                    {"key": "colorways", "label": "Colorways"},
                ]
            },
        }
    ],
}


_DESERT_PACE_TEMPLATE = {
    "id": "desert_pace",
    "name": "Desert Pace Heat-Ready Pack",
    "layoutKey": "fuel_fortress",
    "cover": {
        "titlePlaceholder": "DESERT PACE",
        "subtitlePlaceholder": "HEAT-READY COLLECTION PRESENTED BY RUN VOLUME ONE",
    },
    "stages": [
        {
            "id": "s1",
            "title": "STAGE 01 / DESIGN & TECH DEV.",
            "defaultItems": [
                "Hot-weather use-case notes",
                "Ventilation panel strategy",
                "Tech flats: singlet, short, cap",
                "Fabric shortlist: mesh, micro-pique, ripstop",
            ],
        },
        {
            "id": "s2",
            "title": "STAGE 02 / PRE-PRODUCTION",
            "defaultItems": [
                "Breathability & wicking lab tests",
                "UV protection rating target",
                "Prototype patterns & sample cutting",
                "Updated tech pack + BOM",
            ],
        },
        {
            "id": "s3",
            "title": "STAGE 03 / PRODUCTION",
            "defaultItems": [
                "Size run fit test in motion",
                "Measurement fine-tuning",
                "PPS approval & comments to factory",
                "Inline inspection checklist",
            ],
        },
        {
            "id": "s4",
            "title": "STAGE 04 / MEDIA DIRECTION",
            "defaultItems": [
                "Desert / trail location shortlist",
                "Lighting plan for harsh sun",
                "Editorial vs e-comm shot mix",
                "Launch email + landing page wireframe",
            ],
        },
    ],
    "productBlocks": [
        {
            "id": "pb1",
            "label": "RUNVOLUMEONE",
            "titlePlaceholder": "DESERT PACE AERO SHORT",
            "codePlaceholder": "[CODE: DP-3104]",
            "defaultViews": ["FRONT", "BACK", "SIDE"],
            "detailsTemplate": {
                "fields": [
                    {"key": "styleNumber", "label": "Style #"},
                    {"key": "description", "label": "Description"},
                    {"key": "fabricShell", "label": "Fabric (Shell)"},
                    {"key": "fabricContent", "label": "Fabric Content"},
                    {"key": "sizeRange", "label": "Size Range"},
                    {"key": "colorways", "label": "Colorways"},
                ]
            },
        }
    ],
}


_METRO_INTERVAL_TEMPLATE = {
    "id": "metro_interval",
    "name": "Metro Interval City Commute Line",
    "layoutKey": "fuel_fortress",
    "cover": {
        "titlePlaceholder": "METRO INTERVAL",
        "subtitlePlaceholder": "CITY COMMUTE LINE PRESENTED BY RUN VOLUME ONE",
    },
    "stages": [
        {
            "id": "s1",
            "title": "STAGE 01 / DESIGN & TECH DEV.",
            "defaultItems": [
                "Commute-to-run scenario mapping",
                "Convertible feature ideation",
                "Tech sketches: jacket, pant, packable layer",
                "Fabric matrix: weather-resistant vs stretch",
            ],
        },
        {
            "id": "s2",
            "title": "STAGE 02 / PRE-PRODUCTION",
            "defaultItems": [
                "Fabric handfeel & drape review",
                "Water-repellency and seam sealing tests",
                "Pattern draft for convertible features",
                "Hardware selection: snaps, zips, cords",
            ],
        },
        {
            "id": "s3",
            "title": "STAGE 03 / PRODUCTION",
            "defaultItems": [
                "Function test on prototypes (bike/train/run)",
                "Pattern and spec modifications logged",
                "Final TOP sample approval",
                "Bulk PO + ex-factory timeline",
            ],
        },
        {
            "id": "s4",
            "title": "STAGE 04 / MEDIA DIRECTION",
            "defaultItems": [
                "Transit-focused shot list",
                "BTS content plan for social",
                "Short-form video storyboard",
                "Campaign asset delivery schedule",
            ],
        },
    ],
    "productBlocks": [
        {
            "id": "pb1",
            "label": "RUNVOLUMEONE",
            "titlePlaceholder": "METRO INTERVAL COMMUTER JACKET",
            "codePlaceholder": "[CODE: MI-5507]",
            "defaultViews": ["FRONT", "BACK", "SIDE"],
            "detailsTemplate": {
                "fields": [
                    {"key": "styleNumber", "label": "Style #"},
                    {"key": "description", "label": "Description"},
                    {"key": "fabricShell", "label": "Fabric (Shell)"},
                    {"key": "fabricContent", "label": "Fabric Content"},
                    {"key": "sizeRange", "label": "Size Range"},
                    {"key": "colorways", "label": "Colorways"},
                ]
            },
        }
    ],
}


VOLUMEONE_DB_SCHEMA = [
    {
        "name": "users",
        "label": "Workspace members",
        "description": "Owners and collaborators when you keep auth inside VolumeOne. Safe to skip if you lean entirely on SSO.",
        "optional": True,
        "columns": [
            {"name": "id", "type": "UUID PRIMARY KEY", "notes": "DEFAULT gen_random_uuid()"},
            {"name": "email", "type": "TEXT UNIQUE NOT NULL", "notes": "Primary login + notification channel"},
            {"name": "name", "type": "TEXT", "notes": "Display name"},
            {"name": "created_at", "type": "TIMESTAMPTZ NOT NULL", "notes": "DEFAULT NOW()"},
        ],
    },
    {
        "name": "templates",
        "label": "Reusable template shells",
        "description": "Each pack blueprint (Fuel Fortress, Street Circuit, etc.) with cover copy + layout wiring.",
        "optional": False,
        "columns": [
            {"name": "id", "type": "TEXT PRIMARY KEY", "notes": "slug such as fuel_fortress"},
            {"name": "name", "type": "TEXT NOT NULL", "notes": "Marketing-friendly name"},
            {"name": "layout_key", "type": "TEXT NOT NULL", "notes": "Front-end layout switch"},
            {
                "name": "cover_title_placeholder",
                "type": "TEXT NOT NULL",
                "notes": "Hero headline placeholder",
            },
            {
                "name": "cover_subtitle_placeholder",
                "type": "TEXT NOT NULL",
                "notes": "Hero subtitle placeholder",
            },
            {"name": "created_at", "type": "TIMESTAMPTZ NOT NULL", "notes": "DEFAULT NOW()"},
            {"name": "updated_at", "type": "TIMESTAMPTZ NOT NULL", "notes": "DEFAULT NOW()"},
        ],
    },
    {
        "name": "template_stages",
        "label": "Default stage bullets",
        "description": "Stage scaffolding for each template so projects inherit the same rhythm.",
        "optional": False,
        "columns": [
            {"name": "id", "type": "UUID PRIMARY KEY", "notes": "DEFAULT gen_random_uuid()"},
            {"name": "template_id", "type": "TEXT NOT NULL", "notes": "FK -> templates.id (CASCADE)"},
            {"name": "stage_index", "type": "INT NOT NULL", "notes": "1-based ordering"},
            {"name": "title", "type": "TEXT NOT NULL", "notes": "Stage title (all-caps ok)"},
            {"name": "default_items", "type": "JSONB NOT NULL", "notes": "Ordered bullet copy"},
        ],
        "constraints": ["UNIQUE (template_id, stage_index)"],
    },
    {
        "name": "template_product_blocks",
        "label": "Default product spec blocks",
        "description": "Reusable spec sections per template, including view list + detail field schema.",
        "optional": False,
        "columns": [
            {"name": "id", "type": "UUID PRIMARY KEY", "notes": "DEFAULT gen_random_uuid()"},
            {"name": "template_id", "type": "TEXT NOT NULL", "notes": "FK -> templates.id (CASCADE)"},
            {"name": "block_index", "type": "INT NOT NULL", "notes": "Ordering / block number"},
            {"name": "label", "type": "TEXT NOT NULL", "notes": "Badge like RUNVOLUMEONE"},
            {"name": "title_placeholder", "type": "TEXT NOT NULL", "notes": "e.g. 'AERO HOODIE'"},
            {"name": "code_placeholder", "type": "TEXT", "notes": "Optional code slug"},
            {"name": "default_views", "type": "JSONB NOT NULL", "notes": "List of view labels"},
            {"name": "details_schema", "type": "JSONB NOT NULL", "notes": "Field definitions for spec form"},
        ],
        "constraints": ["UNIQUE (template_id, block_index)"],
    },
    {
        "name": "projects",
        "label": "Live design packs",
        "description": "Each instanced client pack referencing a template snapshot + owner.",
        "optional": False,
        "columns": [
            {"name": "id", "type": "UUID PRIMARY KEY", "notes": "DEFAULT gen_random_uuid()"},
            {"name": "owner_id", "type": "UUID", "notes": "FK -> users.id (nullable when external auth)"},
            {"name": "template_id", "type": "TEXT NOT NULL", "notes": "FK -> templates.id"},
            {"name": "title", "type": "TEXT NOT NULL", "notes": "Project title"},
            {"name": "subtitle", "type": "TEXT", "notes": "Optional subtitle pulled from template"},
            {"name": "client_name", "type": "TEXT", "notes": "Brand / buyer"},
            {"name": "season", "type": "TEXT", "notes": "SS25 / FW25 etc."},
            {"name": "product_type", "type": "TEXT", "notes": "Enum: hoodie, shell, etc."},
            {"name": "status", "type": "TEXT", "notes": "DEFAULT 'draft' (draft/in_progress/approved)"},
            {"name": "created_at", "type": "TIMESTAMPTZ NOT NULL", "notes": "DEFAULT NOW()"},
            {"name": "updated_at", "type": "TIMESTAMPTZ NOT NULL", "notes": "DEFAULT NOW()"},
        ],
    },
    {
        "name": "project_stages",
        "label": "Editable stage content",
        "description": "Concrete bullets for a given project, initially cloned from the template.",
        "optional": False,
        "columns": [
            {"name": "id", "type": "UUID PRIMARY KEY", "notes": "DEFAULT gen_random_uuid()"},
            {"name": "project_id", "type": "UUID NOT NULL", "notes": "FK -> projects.id (CASCADE)"},
            {"name": "template_stage_id", "type": "UUID", "notes": "FK -> template_stages.id (nullable once detached)"},
            {"name": "stage_index", "type": "INT NOT NULL", "notes": "Matches template ordering"},
            {"name": "title", "type": "TEXT NOT NULL", "notes": "Editable title"},
            {"name": "items", "type": "JSONB NOT NULL", "notes": "Editable bullet list"},
            {"name": "created_at", "type": "TIMESTAMPTZ NOT NULL", "notes": "DEFAULT NOW()"},
            {"name": "updated_at", "type": "TIMESTAMPTZ NOT NULL", "notes": "DEFAULT NOW()"},
        ],
        "constraints": ["UNIQUE (project_id, stage_index)"],
    },
    {
        "name": "project_products",
        "label": "Product spec entries",
        "description": "One row per block (i.e., two hoodie variants) with editable copy for factories.",
        "optional": False,
        "columns": [
            {"name": "id", "type": "UUID PRIMARY KEY", "notes": "DEFAULT gen_random_uuid()"},
            {"name": "project_id", "type": "UUID NOT NULL", "notes": "FK -> projects.id (CASCADE)"},
            {
                "name": "template_block_id",
                "type": "UUID",
                "notes": "FK -> template_product_blocks.id (nullable once customized)",
            },
            {"name": "block_index", "type": "INT NOT NULL", "notes": "Ordering / block number"},
            {"name": "label", "type": "TEXT NOT NULL", "notes": "Pack label such as RUNVOLUMEONE"},
            {"name": "title", "type": "TEXT NOT NULL", "notes": "Product title"},
            {"name": "code", "type": "TEXT", "notes": "Optional code displayed on cover"},
            {"name": "style_number", "type": "TEXT", "notes": "Editable field"},
            {"name": "description", "type": "TEXT", "notes": "Editable field"},
            {"name": "fabric_shell", "type": "TEXT", "notes": "Editable field"},
            {"name": "fabric_content", "type": "TEXT", "notes": "Editable field"},
            {"name": "size_range", "type": "TEXT", "notes": "Editable field"},
            {"name": "created_at", "type": "TIMESTAMPTZ NOT NULL", "notes": "DEFAULT NOW()"},
            {"name": "updated_at", "type": "TIMESTAMPTZ NOT NULL", "notes": "DEFAULT NOW()"},
        ],
        "constraints": ["UNIQUE (project_id, block_index)"],
    },
    {
        "name": "product_colorways",
        "label": "Colorway chips",
        "description": "Flexible color rows so merch + marketing can tag swatches beyond the spec body.",
        "optional": False,
        "columns": [
            {"name": "id", "type": "UUID PRIMARY KEY", "notes": "DEFAULT gen_random_uuid()"},
            {"name": "product_id", "type": "UUID NOT NULL", "notes": "FK -> project_products.id (CASCADE)"},
            {"name": "name", "type": "TEXT NOT NULL", "notes": "Display name (Bone, Charcoal)"},
            {"name": "hex_code", "type": "TEXT", "notes": "Optional HEX for swatch previews"},
            {"name": "sort_index", "type": "INT DEFAULT 0", "notes": "Manual ordering"},
        ],
    },
    {
        "name": "project_assets",
        "label": "Linked assets",
        "description": "Flats, lookbook stills, swatches, or logos tied to a project.",
        "optional": False,
        "columns": [
            {"name": "id", "type": "UUID PRIMARY KEY", "notes": "DEFAULT gen_random_uuid()"},
            {"name": "project_id", "type": "UUID NOT NULL", "notes": "FK -> projects.id (CASCADE)"},
            {"name": "type", "type": "TEXT NOT NULL", "notes": "Enum: flat/photo/swatch/logo"},
            {"name": "url", "type": "TEXT NOT NULL", "notes": "Object storage path or CDN URL"},
            {"name": "label", "type": "TEXT", "notes": "Optional caption like 'Front flat'"},
            {"name": "meta", "type": "JSONB", "notes": "Arbitrary metadata e.g. {'view':'FRONT','productBlock':1}"},
            {"name": "created_at", "type": "TIMESTAMPTZ NOT NULL", "notes": "DEFAULT NOW()"},
        ],
    },
]


VOLUMEONE_TEMPLATE_LIBRARY = _build_template_library(
    [
        {
            "summary": "City circuit merch program with reflective-ready outerwear + storyboard-ready bullets.",
            "definition": _STREET_CIRCUIT_TEMPLATE,
        },
        {
            "summary": "Night-run capsule focused on safety requirements, reflective trims, and motion-heavy marketing.",
            "definition": _MIDNIGHT_RELAY_TEMPLATE,
        },
        {
            "summary": "Heat-ready drop for desert or trail events with breathable specs and sun-proof media direction.",
            "definition": _DESERT_PACE_TEMPLATE,
        },
        {
            "summary": "Commute-to-run layering system with convertible hardware callouts and transit media cadence.",
            "definition": _METRO_INTERVAL_TEMPLATE,
        },
    ]
)


def _get_public_contact_email() -> str:
    return (
        getattr(settings, "GLOBALDESIGNERHUB_CONTACT_EMAIL", "")
        or getattr(settings, "PRETTYPEARL_CONTACT_EMAIL", "")
        or getattr(settings, "ADMIN_EMAIL", "")
        or "support@globaldesignerhub.com"
    )


def _format_metric(value: int | None) -> str:
    if not value:
        return "0"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"
    if value >= 1_000:
        return f"{value / 1_000:.1f}".rstrip("0").rstrip(".") + "K"
    return str(value)


def _normalize_caption(text: str | None) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned


def _extract_tags(text: str) -> list[str]:
    if not text:
        return []
    return [match.lower() for match in re.findall(r"#(\w+)", text)]


def _timestamp_to_datetime(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=dt_timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _build_permalink(shortcode: str | None) -> str:
    if shortcode:
        return f"https://www.instagram.com/p/{shortcode}/"
    return _gdh_instagram_profile_url()


def _request_instagram_profile(username: str) -> dict:
    url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
    headers = {
        "User-Agent": VOLUMEONE_USER_AGENT,
        "Accept": "application/json",
        "Referer": f"https://www.instagram.com/{username}/",
        "X-IG-App-ID": VOLUMEONE_INSTAGRAM_APP_ID,
    }
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=10) as response:
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def _transform_instagram_payload(payload: dict, limit: int) -> dict:
    data = (payload or {}).get("data") or {}
    user = data.get("user") or {}
    media = user.get("edge_owner_to_timeline_media") or {}
    edges = media.get("edges") or []

    slides = []
    for edge in edges[:limit]:
        node = edge.get("node") or {}
        caption_edges = (node.get("edge_media_to_caption") or {}).get("edges") or []
        caption_text = caption_edges[0]["node"].get("text") if caption_edges else ""
        caption = _normalize_caption(caption_text)
        taken_at = _timestamp_to_datetime(node.get("taken_at_timestamp"))
        short_caption = caption
        if len(short_caption) > 180:
            short_caption = f"{short_caption[:177].rstrip()}…"
        slides.append(
            {
                "id": node.get("id") or node.get("shortcode"),
                "shortcode": node.get("shortcode"),
                "caption": caption,
                "caption_short": short_caption,
                "image_url": node.get("display_url"),
                "is_video": bool(node.get("is_video")),
                "permalink": _build_permalink(node.get("shortcode")),
                "taken_at": taken_at,
                "tags": _extract_tags(caption),
                "accessibility_caption": node.get("accessibility_caption") or "",
                "like_count": node.get("edge_liked_by", {}).get("count", 0) or 0,
                "like_display": _format_metric(node.get("edge_liked_by", {}).get("count", 0) or 0),
                "comment_count": node.get("edge_media_to_comment", {}).get("count", 0) or 0,
                "comment_display": _format_metric(node.get("edge_media_to_comment", {}).get("count", 0) or 0),
            }
        )

    if not slides:
        raise ValueError("Instagram payload did not include any media edges")

    profile = {
        "handle": user.get("username") or VOLUMEONE_INSTAGRAM_USERNAME,
        "name": user.get("full_name") or "RUNWAY",
        "biography": user.get("biography") or "",
        "followers": user.get("edge_followed_by", {}).get("count", 0) or 0,
        "following": user.get("edge_follow", {}).get("count", 0) or 0,
        "posts": media.get("count", len(slides)) or len(slides),
        "avatar_url": user.get("profile_pic_url_hd") or "",
    }
    profile["followers_display"] = _format_metric(profile["followers"])
    profile["following_display"] = _format_metric(profile["following"])
    profile["posts_display"] = _format_metric(profile["posts"])

    return {
        "profile": profile,
        "slides": slides,
        "source": "live",
        "fetched_at": timezone.now(),
    }


def _volumeone_fallback_feed(limit: int) -> dict:
    now = timezone.now()
    slides = []
    for raw in VOLUMEONE_FALLBACK_SLIDES[:limit]:
        caption = _normalize_caption(raw.get("caption"))
        taken_at = _timestamp_to_datetime(raw.get("timestamp")) or now
        short_caption = caption
        if len(short_caption) > 180:
            short_caption = f"{short_caption[:177].rstrip()}…"
        slides.append(
            {
                "id": raw.get("shortcode"),
                "shortcode": raw.get("shortcode"),
                "caption": caption,
                "caption_short": short_caption,
                "image_url": raw.get("image_url"),
                "is_video": bool(raw.get("is_video")),
                "permalink": _build_permalink(raw.get("shortcode")),
                "taken_at": taken_at,
                "tags": _extract_tags(caption),
                "accessibility_caption": "",
                "like_count": raw.get("like_count", 0) or 0,
                "like_display": _format_metric(raw.get("like_count", 0) or 0),
                "comment_count": raw.get("comment_count", 0) or 0,
                "comment_display": _format_metric(raw.get("comment_count", 0) or 0),
            }
        )

    profile = {
        **VOLUMEONE_FALLBACK_PROFILE,
        "followers_display": _format_metric(VOLUMEONE_FALLBACK_PROFILE.get("followers", 0)),
        "following_display": _format_metric(VOLUMEONE_FALLBACK_PROFILE.get("following", 0)),
        "posts_display": _format_metric(VOLUMEONE_FALLBACK_PROFILE.get("posts", 0)),
    }

    return {
        "profile": profile,
        "slides": slides,
        "source": "fallback",
        "fetched_at": now,
    }


def get_volumeone_feed(limit: int = VOLUMEONE_DEFAULT_SLIDES) -> dict:
    limit = max(1, min(int(limit or VOLUMEONE_DEFAULT_SLIDES), VOLUMEONE_MAX_SLIDES))
    cache_key = f"{VOLUMEONE_FEED_CACHE_KEY}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        payload = _request_instagram_profile(VOLUMEONE_INSTAGRAM_USERNAME)
        feed = _transform_instagram_payload(payload, limit)
        cache.set(cache_key, feed, VOLUMEONE_FEED_CACHE_TTL)
        return feed
    except Exception as exc:
        logger.warning("Falling back to cached VolumeOne feed: %s", exc, exc_info=isinstance(exc, (HTTPError, URLError)))
        fallback = _volumeone_fallback_feed(limit)
        cache.set(cache_key, fallback, 300)
        return fallback


def _get_volumeone_design_packs() -> list[dict]:
    """Collect TekPak blueprint metadata for the VolumeOne showcase."""
    packs: list[dict] = []
    for slug in VOLUMEONE_DESIGN_PACK_SLUGS:
        blueprint = get_techpack_blueprint(slug)
        if not blueprint:
            continue

        hero = blueprint.get("hero", {})
        project_breakdown = blueprint.get("project_breakdown", {})
        colorways = (blueprint.get("colorways") or [])[:3]

        try:
            techpack_url = reverse("generate_techpack", args=[slug])
        except NoReverseMatch:
            techpack_url = f"/generate-techpack/{slug}/"

        packs.append(
            {
                "slug": slug,
                "title": hero.get("title")
                or blueprint.get("title")
                or slug.replace("-", " ").title(),
                "subtitle": hero.get("subtitle") or project_breakdown.get("kicker", ""),
                "badge": hero.get("badge", ""),
                "icon": hero.get("icon", ""),
                "supporting_copy": (hero.get("supporting_copy") or [])[:2],
                "project_breakdown_label": project_breakdown.get("label", ""),
                "stage_count": len(blueprint.get("stages") or []),
                "colorways": colorways,
                "url": techpack_url,
            }
        )
    return packs


def _base64url_from_bytes(value: bytes) -> str:
    if not isinstance(value, (bytes, bytearray)):
        raise TypeError("value must be bytes")
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _bytes_from_base64url(data: str) -> bytes:
    if not isinstance(data, str):
        raise TypeError("data must be str")
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _doc_category_parts(value: str):
    """
    Normalize documentation categories so we can build URLs safely.
    Returns (raw_value, label, slug).
    """

    raw_value = (value or "").strip()
    label = raw_value or "General"
    slug_value = slugify(label) or "general"
    return raw_value, label, slug_value


def _doc_categories_with_counts():
    """
    Return a list of dicts describing available documentation categories.
    """

    categories = []
    qs = (
        DocPage.objects.filter(published=True)
        .values("category")
        .annotate(total=Count("id"))
        .order_by("category")
    )

    for row in qs:
        raw_value, label, slug_value = _doc_category_parts(row["category"])
        categories.append(
            {
                "value": raw_value,
                "label": label,
                "slug": slug_value,
                "total": row["total"],
            }
        )

    if not categories:
        categories.append(
            {
                "value": "",
                "label": "General",
                "slug": "general",
                "total": 0,
            }
        )

    return categories


def _filter_docs_by_category(queryset, category_value: str):
    """
    Apply category filter to a DocPage queryset, supporting empty/default categories.
    """

    normalized_value = (category_value or "").strip()
    if not normalized_value:
        return queryset.filter(Q(category__isnull=True) | Q(category=""))
    return queryset.filter(category=normalized_value)


def _request_wants_json(request) -> bool:
    requested_with = (request.headers.get("x-requested-with") or "").lower()
    if requested_with == "xmlhttprequest":
        return True
    accept_header = request.headers.get("Accept") or ""
    if "application/json" in accept_header:
        return True
    content_type = request.headers.get("Content-Type") or ""
    return content_type.startswith("application/json")


def _strtobool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _safe_file_url(file_field) -> str:
    """
    Return a safe URL for an uploaded file, handling missing or unloaded files gracefully.
    """

    if not file_field:
        return ""
    try:
        return file_field.url
    except (ValueError, AttributeError):
        return ""


def _infer_media_type(file_name: str) -> str:
    """
    Infer whether a media asset should be treated as an image or video based on its extension.
    """

    suffix = Path(file_name or "").suffix.lower()
    return "video" if suffix in RUNWAY_VIDEO_EXTENSIONS else "image"


def _default_field_label(key: str) -> str:
    """Turn data keys into readable labels."""
    key = (key or "").strip()
    if not key:
        return "Field"
    buffer = []
    prev_lower = False
    for char in key:
        if char in {"_", "-"}:
            buffer.append(" ")
            prev_lower = False
            continue
        if char.isupper() and prev_lower:
            buffer.append(" ")
        buffer.append(char)
        prev_lower = char.isalpha() and char.islower()
    label = "".join(buffer).strip()
    return label.title() or "Field"


def _coerce_spec_field(field_definition):
    if isinstance(field_definition, dict):
        key = (field_definition.get("key") or "").strip()
        label = (field_definition.get("label") or "").strip()
    else:
        key = str(field_definition or "").strip()
        label = ""
    if not key and label:
        key = slugify(label).replace("-", "_")
    if not key:
        key = "field"
    label = label or _default_field_label(key)
    return key, label


def _copy_template_blueprint(project: Project, template_source, snapshot: dict | None = None) -> None:
    if isinstance(template_source, Template):
        stage_entries = [
            {
                "template_stage": stage,
                "stage_number": stage.stage_index or order,
                "title": stage.title or f"Stage {order}",
                "layout_hint": stage.layout_hint or "",
                "items": list(stage.default_items or []),
            }
            for order, stage in enumerate(template_source.stages.all(), start=1)
        ]
        block_entries = [
            {
                "template_block": block,
                "block_index": block.block_index or order,
                "label": block.label or template_source.name,
                "title": block.title_placeholder or block.label or template_source.name,
                "code": block.code_placeholder or "",
                "default_views": list(block.default_views or []),
                "details": block.details_schema or {},
            }
            for order, block in enumerate(template_source.product_blocks.all(), start=1)
        ]
    else:
        template_definition = template_source or {}
        stage_entries = []
        for idx, stage_info in enumerate(template_definition.get("stages") or [], start=1):
            items = stage_info.get("defaultBullets") or stage_info.get("defaultItems") or []
            stage_entries.append(
                {
                    "template_stage": None,
                    "stage_number": stage_info.get("stageNumber") or idx,
                    "title": stage_info.get("title") or f"Stage {idx}",
                    "layout_hint": stage_info.get("layoutHint", ""),
                    "items": [str(item).strip() for item in items if str(item).strip()],
                }
            )

        block_entries = []
        product_blocks = template_definition.get("productBlocks") or []
        if not product_blocks and template_definition.get("productSpec"):
            spec = template_definition["productSpec"]
            product_blocks = [
                {
                    "label": template_definition.get("name") or template_definition.get("id") or "Product",
                    "titlePlaceholder": spec.get("title") or "Product Spec",
                    "codePlaceholder": spec.get("code") or "",
                    "defaultViews": spec.get("defaultViews") or [],
                    "detailsTemplate": {"fields": spec.get("fields") or []},
                }
            ]

        for idx, block in enumerate(product_blocks, start=1):
            block_entries.append(
                {
                    "template_block": None,
                    "block_index": block.get("blockIndex") or block.get("block_index") or idx,
                    "label": block.get("label") or template_definition.get("name") or "Product",
                    "title": block.get("titlePlaceholder") or block.get("title") or "Product Spec",
                    "code": block.get("codePlaceholder") or block.get("code") or "",
                    "default_views": block.get("defaultViews") or [],
                    "details": block.get("detailsTemplate") or block.get("details_schema") or {},
                }
            )

    stages_to_use = stage_entries or []
    for idx, stage_data in enumerate(stages_to_use, start=1):
        items = stage_data.get("items") or []
        stage = ProjectStage.objects.create(
            project=project,
            template_stage=stage_data.get("template_stage"),
            stage_number=stage_data.get("stage_number") or idx,
            title=stage_data.get("title") or f"Stage {idx}",
            layout_hint=stage_data.get("layout_hint", ""),
            order=idx,
            items=items,
        )
        for bullet_idx, bullet in enumerate(items, start=1):
            text = (bullet or "").strip()
            if not text:
                continue
            ProjectStageBullet.objects.create(
                stage=stage,
                order=bullet_idx,
                text=text,
            )

    blocks_to_use = block_entries or []
    if not blocks_to_use and snapshot:
        spec = snapshot.get("productSpec") or {}
        fields = spec.get("fields") or []
        block = ProjectProductSpec.objects.create(
            project=project,
            title=spec.get("title") or "Product Spec",
            layout_key=spec.get("layoutHint", ""),
        )
        for order, field_definition in enumerate(fields, start=1):
            field_key, label = _coerce_spec_field(field_definition)
            ProjectProductSpecField.objects.create(
                product_spec=block,
                field_key=field_key,
                label=label,
                order=order,
            )
        return

    for block_data in blocks_to_use:
        details = block_data.get("details") or {}
        spec = ProjectProductSpec.objects.create(
            project=project,
            template_block=block_data.get("template_block"),
            block_index=block_data.get("block_index") or 1,
            label=block_data.get("label") or "",
            title=block_data.get("title") or "Product Spec",
            code=block_data.get("code") or "",
            layout_key=details.get("layoutHint", ""),
            default_views=block_data.get("default_views") or [],
        )
        for order, field_definition in enumerate(details.get("fields") or [], start=1):
            field_key, label = _coerce_spec_field(field_definition)
            ProjectProductSpecField.objects.create(
                product_spec=spec,
                field_key=field_key,
                label=label,
                order=order,
            )


def build_runway_collection_payload(collection, *, placeholder_url: str, guest_link_days: int) -> dict:
    """
    Build a normalized payload for a Collection so templates can render cards, list rows,
    and detail modals without duplicating logic.
    """

    cover_url = _safe_file_url(getattr(collection, "cover_image", None))
    gallery_rel = getattr(collection, "gallery", None)
    look_rel = getattr(collection, "looks", None)

    gallery_items = list(gallery_rel.all()) if gallery_rel is not None else []
    look_items = list(look_rel.all()) if look_rel is not None else []

    media_assets = []
    for asset in gallery_items:
        asset_url = _safe_file_url(getattr(asset, "image", None))
        if not asset_url:
            continue
        media_assets.append(
            {
                "type": _infer_media_type(getattr(asset.image, "name", "")),
                "url": asset_url,
                "name": asset.caption or collection.name,
                "caption": asset.caption or "",
            }
        )

    lookbook_entries = []
    attachments_count = 0

    for look in look_items:
        look_image_url = _safe_file_url(getattr(look, "image", None))
        has_specs = any(
            [
                bool(getattr(look, "measurements", "")),
                bool(getattr(look, "notes", "")),
                bool(getattr(look, "fabric", "")),
            ]
        )
        if has_specs:
            attachments_count += 1

        entry = {
            "number": getattr(look, "look_number", len(lookbook_entries) + 1),
            "title": getattr(look, "title", "") or f"Look {getattr(look, 'look_number', len(lookbook_entries) + 1)}",
            "description": getattr(look, "description", ""),
            "image": look_image_url,
            "fabric": getattr(look, "fabric", ""),
            "measurements": getattr(look, "measurements", ""),
            "notes": getattr(look, "notes", ""),
            "has_specs": has_specs,
        }
        lookbook_entries.append(entry)

        if look_image_url:
            media_assets.append(
                {
                    "type": "image",
                    "url": look_image_url,
                    "name": entry["title"],
                    "caption": entry["description"],
                }
            )

    if not cover_url and media_assets:
        cover_url = media_assets[0]["url"]

    cover_url = cover_url or placeholder_url
    look_count = len(lookbook_entries)
    has_motion = any(asset["type"] == "video" for asset in media_assets)
    status_badge = "Viewer ready" if getattr(collection, "published", True) else "Private review"
    access_scope = "Public viewers & guests" if getattr(collection, "published", True) else "Invite-only"
    try:
        view_url = reverse("collection_detail", kwargs={"slug": collection.slug})
    except NoReverseMatch:
        view_url = ""

    capabilities = []
    if look_count:
        capabilities.append("Lookbook")
    if attachments_count:
        capabilities.append("Tech packs")
    if has_motion:
        capabilities.append("Motion")
    if cover_url and cover_url != placeholder_url:
        capabilities.append("Cover imagery")
    capabilities.append("Embed-ready")
    if getattr(collection, "published", True):
        capabilities.append("Public")
    else:
        capabilities.append("Private review")

    list_summary = f"{look_count or 0} looks • {attachments_count} attachments • {status_badge}"

    return {
        "id": getattr(collection, "id", None),
        "name": getattr(collection, "name", "Untitled Capsule"),
        "slug": getattr(collection, "slug", ""),
        "season": getattr(collection, "season", "") or "Runway Capsule",
        "year": getattr(collection, "year", ""),
        "designer": getattr(collection, "designer", "") or "Independent Studio",
        "description": getattr(collection, "description", "") or "Runway-ready capsule",
        "cover_image_url": cover_url,
        "cover_uses_placeholder": cover_url == placeholder_url,
        "look_count": look_count,
        "attachment_count": attachments_count,
        "gallery_count": len(media_assets),
        "has_motion": has_motion,
        "capabilities": capabilities,
        "published": getattr(collection, "published", True),
        "status_badge": status_badge,
        "access_scope": access_scope,
        "guest_link_expiry_days": guest_link_days,
        "lookbook_version": f"v{getattr(collection, 'year', timezone.now().year)}.{max(1, look_count or attachments_count or 1)}",
        "version_label": f"{(getattr(collection, 'season', '') or 'Runway')} {getattr(collection, 'year', '')}",
        "media": media_assets,
        "lookbook": lookbook_entries,
        "view_url": view_url,
        "sharing_label": "Copy public link" if getattr(collection, "published", True) else "Send guest review link",
        "security_summary": f"Guest links auto-expire after {guest_link_days} days.",
        "list_summary": list_summary,
        "embedding_ready": bool(media_assets),
        "created_at": getattr(collection, "created_at", None),
    }


def _save_design_from_request(request, *, design=None):
    """
    Create or update a Design instance based on the incoming request data.
    Returns a tuple of (design_instance, errors_dict).
    """

    user = request.user
    is_create = design is None
    instance = design or Design(designer=user)

    data = request.POST
    files = request.FILES
    errors = {}

    # Core fields
    title = (data.get("title") or "").strip()
    if not title:
        errors["title"] = "Design title is required."

    season = (data.get("season") or "").strip()
    if not season:
        errors["season"] = "Season is required."

    year_raw = (data.get("year") or "").strip()
    year_value = instance.year
    if year_raw:
        try:
            year_value = int(year_raw)
        except ValueError:
            errors["year"] = "Enter a valid year."
    elif is_create:
        errors["year"] = "Year is required."

    slug_input = (data.get("slug") or "").strip()
    if slug_input:
        slug_qs = Design.objects.filter(slug__iexact=slug_input)
        if instance.pk:
            slug_qs = slug_qs.exclude(pk=instance.pk)
        if slug_qs.exists():
            errors["slug"] = "Another design is already using this URL slug."

    cover_image_file = files.get("cover_image")
    if is_create and not (cover_image_file or instance.cover_image):
        errors["cover_image"] = "Please provide a cover image for this design."

    target_price_value = None
    target_price_raw = (data.get("target_price") or "").strip()
    if target_price_raw:
        try:
            target_price_value = Decimal(target_price_raw)
        except InvalidOperation:
            errors["target_price"] = "Enter a valid price (e.g., 199.99)."

    # Tech pack uploads
    pdf_upload = files.get("techpack_pdf")
    excel_upload = files.get("techpack_excel")
    techpack_combo_file = files.get("techpack_file")
    if techpack_combo_file:
        extension = Path(techpack_combo_file.name).suffix.lower()
        if extension == ".pdf":
            pdf_upload = techpack_combo_file
        elif extension in {".xls", ".xlsx"}:
            excel_upload = techpack_combo_file
        else:
            errors["techpack_file"] = "Unsupported tech pack format. Upload PDF or Excel files."

    additional_images = files.getlist("additional_images")

    if errors:
        return instance, errors

    # Assign basic fields
    instance.title = title
    instance.season = season
    instance.year = year_value
    instance.description = (data.get("description") or "").strip()

    # Classification & metadata
    instance.category = (data.get("category") or "").strip()
    instance.target_market = (data.get("target_market") or "").strip()
    instance.featured = _strtobool(data.get("featured")) or _strtobool(data.get("is_featured"))

    instance.fabric_type = (data.get("fabric_type") or "").strip()
    instance.fabric_weight = (data.get("fabric_weight") or "").strip()
    fabric_details_input = (data.get("fabric_details") or "").strip()
    if not fabric_details_input:
        fabric_details_input = ", ".join(
            filter(None, [instance.fabric_type, instance.fabric_weight])
        )
    instance.fabric_details = fabric_details_input

    instance.color_palette = (data.get("color_palette") or "").strip()
    instance.size_range = (data.get("size_range") or "").strip()
    instance.target_price = target_price_value

    technical_notes = (
        data.get("technical_notes")
        or data.get("production_notes")
        or ""
    )
    instance.production_notes = technical_notes.strip()
    instance.design_notes = (data.get("design_notes") or "").strip()

    published_flag = _strtobool(data.get("published")) or _strtobool(data.get("is_public"))
    instance.published = published_flag

    if slug_input:
        instance.slug = slug_input

    if cover_image_file:
        instance.cover_image = cover_image_file

    if pdf_upload:
        instance.techpack_pdf = pdf_upload
    if excel_upload:
        instance.techpack_excel = excel_upload

    # Validate model-level constraints
    try:
        instance.full_clean(exclude=["slug"])
    except ValidationError as exc:
        for field_name, messages_list in exc.message_dict.items():
            if not messages_list:
                continue
            combined_message = " ".join(str(message) for message in messages_list)
            errors[field_name] = combined_message

    if errors:
        return instance, errors

    instance.save()

    # Attach additional gallery images
    if additional_images:
        existing_count = instance.images.count()
        for offset, image_file in enumerate(additional_images, start=1):
            DesignImage.objects.create(
                design=instance,
                image=image_file,
                order=existing_count + offset,
            )

    return instance, {}


def _find_user_by_identifier(identifier: str):
    identifier = (identifier or "").strip()
    if not identifier:
        return None

    UserModel = get_user_model()

    try:
        return UserModel.objects.get(username__iexact=identifier)
    except UserModel.DoesNotExist:
        try:
            return UserModel.objects.get(email__iexact=identifier)
        except UserModel.DoesNotExist:
            return None


def _signup_template_context(form: DesignerSignUpForm) -> dict:
    return {"form": form, **recaptcha_template_context()}


def signup_view(request):
    if getattr(settings, "GOOGLE_LOGIN_MANDATORY", False):
        messages.info(
            request,
            "New accounts are created by signing in with Gmail. Use Continue with Google on the login page.",
        )
        return redirect(reverse("login") + "?next=" + request.GET.get("next", "/"))
    if request.method == "POST":
        # Attempt to restore an existing but inactive account based on username/email
        desired_username = (request.POST.get("username") or "").strip()
        email_input = (request.POST.get("email") or "").strip().lower()
        website_url = (request.POST.get("website_url") or "").strip()
        password1 = request.POST.get("password1") or ""
        password2 = request.POST.get("password2") or ""
        recaptcha_token = (request.POST.get("g-recaptcha-response") or "").strip()

        recaptcha_ok, recaptcha_error = verify_recaptcha_token(
            recaptcha_token, remote_ip=request.META.get("REMOTE_ADDR")
        )
        if not recaptcha_ok:
            form = DesignerSignUpForm(request.POST)
            form.add_error(None, recaptcha_error)
            messages.error(request, "Please complete the reCAPTCHA challenge.")
            return render(request, "registration/signup.html", _signup_template_context(form))

        if password1 and password1 == password2:
            inactive_user = (
                User.objects.filter(
                    Q(is_active=False),
                    Q(username__iexact=desired_username) | Q(email__iexact=email_input),
                )
                .order_by("id")
                .first()
            )

            if inactive_user is not None:
                # Validate password strength before restoring
                try:
                    validate_password(password1, user=inactive_user)
                except ValidationError as exc:
                    form = DesignerSignUpForm(request.POST)
                    form.add_error("password1", exc)
                    messages.error(request, "Please correct the errors below.")
                    return render(request, "registration/signup.html", _signup_template_context(form))

                # Restore user account
                inactive_user.is_active = True
                if email_input:
                    inactive_user.email = email_input
                inactive_user.set_password(password1)
                inactive_user.save()

                # Ensure related records exist
                ensure_designer_access(inactive_user)
                profile = inactive_user.designer_profile
                # Persist optional website URL if valid
                if website_url:
                    try:
                        URLValidator()(website_url)
                        profile.portfolio_website = website_url
                        profile.save()
                    except ValidationError:
                        # Ignore invalid URL in restore path; do not block restore
                        pass

                # Credit referral if present (restored-user path)
                ref_code = request.session.pop("referral_code", None)
                ref_source = request.session.pop("referral_source", None)
                try:
                    from .services.referrals import credit_referral_on_signup
                    credit_referral_on_signup(
                        user=inactive_user,
                        referral_code=ref_code,
                        source=ref_source,
                        ip=request.META.get("REMOTE_ADDR"),
                        ua=request.META.get("HTTP_USER_AGENT"),
                    )
                except Exception:
                    pass

                # Log the user in using identifier they provided (email or username)
                user_identifier = email_input or desired_username
                user_auth = authenticate(request, username=user_identifier, password=password1)
                if user_auth is not None and user_auth.is_active:
                    login(request, user_auth)
                    return redirect("designer_dashboard")

                messages.success(request, "Account restored. Please log in.")
                return redirect("login")

        # Fall back to normal signup flow
        form = DesignerSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            ref_code = request.session.pop("referral_code", None)
            ref_source = request.session.pop("referral_source", None)
            try:
                from .services.referrals import credit_referral_on_signup
                credit_referral_on_signup(
                    user=user,
                    referral_code=ref_code,
                    source=ref_source,
                    ip=request.META.get("REMOTE_ADDR"),
                    ua=request.META.get("HTTP_USER_AGENT"),
                )
            except Exception:
                pass
            transaction.on_commit(
                lambda: send_registration_notifications(user, request=request, source="ui")
            )
            raw_password = form.cleaned_data.get("password1")
            user_auth = authenticate(request, username=user.username, password=raw_password)
            if user_auth is not None and user_auth.is_active:
                login(request, user_auth)
                return redirect("designer_dashboard")
            messages.success(request, "Account created. Please log in.")
            return redirect("login")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DesignerSignUpForm()

    return render(request, "registration/signup.html", _signup_template_context(form))

# Basic view classes for URL compatibility
class HomePageView(TemplateView):
    template_name = "designer_portfolio/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Provide featured designers for the homepage slideshow.
        # Currently: show the latest active designer profiles (up to 8).
        # If curation is needed later, add a boolean flag on DesignerProfile and filter by it.
        try:
            designers_qs = (
                DesignerProfile.objects.filter(user__is_active=True)
                .select_related("user")
                .order_by("-created_at")
            )
            context["designers"] = list(designers_qs[:8])
        except Exception:
            # Fallback to an empty list if the database or model is unavailable
            context["designers"] = []
        
        # Provide collections for the homepage slideshow
        try:
            collections_qs = Collection.objects.order_by("-year", "name")
            context["collections"] = list(collections_qs)
        except Exception:
            # Fallback to an empty list if the database or model is unavailable
            context["collections"] = []

        # Highlight the global footprint of the designer community
        context["global_fashion_cities"] = [
            {
                "name": "Paris",
                "region": "France",
                "flag": "🇫🇷",
                "tagline": "Haute couture heritage with boundary-pushing ateliers.",
                "signature_style": "Couture story-driven runway",
                "spotlight_event": "Paris Fashion Week",
                "specialties": ["Couture", "Luxury ready-to-wear", "Maison ateliers"],
            },
            {
                "name": "New York",
                "region": "United States",
                "flag": "🇺🇸",
                "tagline": "Editorial energy meets street-ready sophistication.",
                "signature_style": "Runway-to-retail innovation",
                "spotlight_event": "New York Fashion Week",
                "specialties": ["Streetwear", "Editorial styling", "Fashion tech"],
            },
            {
                "name": "Mumbai (Bombay)",
                "region": "India",
                "flag": "🇮🇳",
                "tagline": "Cinematic drama and craft-first couture.",
                "signature_style": "Embellished occasionwear",
                "spotlight_event": "Lakme Fashion Week",
                "specialties": ["Bridal couture", "Surface embellishment", "Textile innovation"],
            },
            {
                "name": "Hyderabad",
                "region": "India",
                "flag": "🇮🇳",
                "tagline": "Heritage textiles reimagined for modern silhouettes.",
                "signature_style": "Handloom luxury",
                "spotlight_event": "Hyderabad Couture Week",
                "specialties": ["Handloom", "Occasionwear", "Fusion couture"],
            },
            {
                "name": "Los Angeles",
                "region": "United States",
                "flag": "🇺🇸",
                "tagline": "Red-carpet polish meets sustainable fabrication.",
                "signature_style": "Cinematic ready-to-wear",
                "spotlight_event": "LAFW",
                "specialties": ["Red carpet", "Eco-luxury", "Celebrity styling"],
            },
            {
                "name": "Milan",
                "region": "Italy",
                "flag": "🇮🇹",
                "tagline": "Tailored precision and iconic maisons.",
                "signature_style": "Architectural tailoring",
                "spotlight_event": "Milan Fashion Week",
                "specialties": ["Luxury tailoring", "Leather craftsmanship", "Accessories"],
            },
            {
                "name": "London",
                "region": "United Kingdom",
                "flag": "🇬🇧",
                "tagline": "Avant-garde experimentation with heritage craft.",
                "signature_style": "Concept-led collections",
                "spotlight_event": "London Fashion Week",
                "specialties": ["Avant-garde", "Textile labs", "Graduate showcases"],
            },
            {
                "name": "Tokyo",
                "region": "Japan",
                "flag": "🇯🇵",
                "tagline": "Precision construction balanced with playful storytelling.",
                "signature_style": "Tech-informed silhouettes",
                "spotlight_event": "Rakuten Fashion Week Tokyo",
                "specialties": ["Techwear", "Experimental patternmaking", "Street luxury"],
            },
            {
                "name": "Seoul",
                "region": "South Korea",
                "flag": "🇰🇷",
                "tagline": "Pop-culture influence driving bold ready-to-wear.",
                "signature_style": "K-fashion future classics",
                "spotlight_event": "Seoul Fashion Week",
                "specialties": ["K-fashion", "Beauty crossovers", "Digital drops"],
            },
            {
                "name": "Dubai",
                "region": "United Arab Emirates",
                "flag": "🇦🇪",
                "tagline": "Luxury resortwear for a global audience.",
                "signature_style": "Opulent resort couture",
                "spotlight_event": "Dubai Fashion Week",
                "specialties": ["Modest luxury", "Resortwear", "Fashion entrepreneurship"],
            },
        ]

        context["regional_hiring_areas"] = REGIONAL_HIRING_AREAS

        forum_url = getattr(
            settings,
            "COMMUNITY_FORUM_URL",
            "https://community.globaldesignerhub.com",
        )
        context["community_forum_url"] = forum_url
        context["lead_generation_tools"] = [
            {
                "title": "Contact inquiry forms",
                "icon": "fa-regular fa-paper-plane",
                "description": "Visitors can send project requests directly from a designer profile.",
            },
            {
                "title": "Request a quote",
                "icon": "fa-solid fa-file-invoice-dollar",
                "description": "Brands can ask for pricing, timelines, and project estimates before committing.",
            },
            {
                "title": "Book a consultation",
                "icon": "fa-regular fa-calendar-check",
                "description": "Schedule discovery calls for tech packs, CLO3D, pattern making, or full collections.",
            },
            {
                "title": "Direct messaging",
                "icon": "fa-regular fa-comments",
                "description": "Clients and designers keep introductions, questions, and next steps inside the platform.",
            },
            {
                "title": "Portfolio inquiries",
                "icon": "fa-solid fa-shirt",
                "description": "Visitors can ask about a specific design, collection, or service package.",
            },
            {
                "title": "Project request forms",
                "icon": "fa-solid fa-list-check",
                "description": "Brands can submit requirements for tech packs, fashion design, CLO3D, and production prep.",
            },
            {
                "title": "Email notifications",
                "icon": "fa-regular fa-bell",
                "description": "Designers receive instant alerts when a new lead arrives.",
            },
            {
                "title": "Analytics dashboard",
                "icon": "fa-solid fa-chart-line",
                "description": "Track profile views, inquiries, and conversion signals from visitor to client.",
            },
        ]
        context["global_designer_features"] = [
            {
                "title": "Global designer profiles",
                "icon": "fa-solid fa-id-card-clip",
                "description": (
                    "Verified bios, specialties, and regions show up next to every portfolio, pitch deck, "
                    "and thread so collaborators immediately know your strengths."
                ),
                "bullets": [
                    "Rich profile cards in the Designers directory",
                    "Link collections, awards, and preferred markets",
                ],
                "cta": {
                    "label": "Explore designers",
                    "href": reverse("designers_list"),
                    "icon": "fa-solid fa-user-group",
                },
            },
            {
                "title": "Runway-ready collections",
                "icon": "fa-solid fa-layer-group",
                "description": (
                    "Publish collections with lookbooks, motion, and tech pack attachments. "
                    "Share private review links or embed them across your site."
                ),
                "bullets": [
                    "Versioned lookbooks with cover imagery",
                    "Guest links expire automatically for security",
                ],
                "cta": {
                    "label": "View collections",
                    "href": reverse("collections"),
                    "icon": "fa-solid fa-photo-film",
                },
            },
            {
                "title": "Designer AI copilot",
                "icon": "fa-solid fa-robot",
                "description": (
                    "Ask portfolio questions, summarize briefs, or draft outreach messages using the embedded "
                    "Designer AI assistant tuned for GlobalDesignerHub workflows."
                ),
                "bullets": [
                    "Instant answers sourced from your docs",
                    "Multi-language and session history support",
                ],
                "cta": {
                    "label": "Open Designer AI",
                    "href": reverse("designer_ai_history"),
                    "icon": "fa-solid fa-sparkles",
                },
            },
            {
                "title": "Community forum + events",
                "icon": "fa-solid fa-comments",
                "description": (
                    "Swap build-in-public updates, RSVP to AMAs, and tap Designer AI summaries directly "
                    "inside threads with the GlobalDesignerHub community."
                ),
                "bullets": [
                    "120+ curated topic filters and event recaps",
                    "Flag issues or invite partners in seconds",
                ],
                "cta": {
                    "label": "Visit Community Forum",
                    "href": forum_url,
                    "target": "_blank",
                    "rel": "noopener",
                    "icon": "fa-solid fa-arrow-up-right-from-square",
                },
            },
        ]

        return context

class StudentPageView(TemplateView):
    template_name = "designer_portfolio/student.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "student_primary_cta": reverse("signup"),
                "student_secondary_cta": reverse("designers_list"),
                "student_focus_tracks": [
                    {
                        "title": "Portfolio launch plan",
                        "description": (
                            "Build a complete portfolio with collections, process documentation, and project-ready "
                            "presentation pages that can be shared with mentors or recruiters."
                        ),
                    },
                    {
                        "title": "Mentor-style feedback loop",
                        "description": (
                            "Ask Designer AI for critique prompts, prep interview talking points, and shape your "
                            "next iteration with structured guidance."
                        ),
                    },
                    {
                        "title": "Career-ready collaboration",
                        "description": (
                            "Connect with designers in the directory, explore events, and learn how studios "
                            "communicate expectations before production starts."
                        ),
                    },
                ],
                "student_resource_cards": [
                    {
                        "title": "Free trial access",
                        "description": "Create your account, upload work, and explore every feature before committing.",
                        "icon": "fa-solid fa-graduation-cap",
                        "cta_label": "Start your free trial",
                        "cta_href": reverse("signup"),
                    },
                    {
                        "title": "Live designer directory",
                        "description": "Study real portfolio structures, specialties, and service packages in one place.",
                        "icon": "fa-solid fa-user-group",
                        "cta_label": "Browse designers",
                        "cta_href": reverse("designers_list"),
                    },
                    {
                        "title": "Events + community",
                        "description": "Follow showcases, AMAs, and discussions to stay plugged into current workflows.",
                        "icon": "fa-solid fa-comments",
                        "cta_label": "Join community",
                        "cta_href": reverse("community_redirect"),
                    },
                ],
                "student_launch_checklist": [
                    {
                        "title": "1. Create your account",
                        "description": "Sign up with email or Google and choose your portfolio direction.",
                    },
                    {
                        "title": "2. Upload your strongest projects",
                        "description": "Start with one polished collection, then add process and supporting visuals.",
                    },
                    {
                        "title": "3. Refine with Designer AI",
                        "description": "Use guided prompts to improve structure, captions, and project storytelling.",
                    },
                    {
                        "title": "4. Share and grow",
                        "description": "Send your portfolio to peers, mentors, and collaborators as you build momentum.",
                    },
                ],
            }
        )
        return context


# Dress types for new orders page (viewer-facing)
DRESS_TYPES = [
    ("evening", "Evening Dress"),
    ("cocktail", "Cocktail Dress"),
    ("day", "Day Dress"),
    ("maxi", "Maxi Dress"),
    ("mini", "Mini Dress"),
    ("midi", "Midi Dress"),
    ("bridal", "Bridal / Wedding"),
    ("casual", "Casual"),
    ("formal", "Formal"),
    ("party", "Party Wear"),
]

# Fabric types for new orders page
FABRIC_TYPES = [
    ("cotton", "Cotton"),
    ("silk", "Silk"),
    ("wool", "Wool"),
    ("linen", "Linen"),
    ("polyester", "Polyester"),
    ("satin", "Satin"),
    ("velvet", "Velvet"),
    ("chiffon", "Chiffon"),
    ("jersey", "Jersey"),
    ("tweed", "Tweed"),
]

# Wool types (when Wool fabric is selected)
WOOL_TYPES = [
    ("", "— Select wool type —"),
    ("merino", "Merino"),
    ("lambswool", "Lambswool"),
    ("cashmere", "Cashmere"),
    ("shetland", "Shetland"),
    ("alpaca", "Alpaca"),
    ("mohair", "Mohair"),
]

# Fabric textures
FABRIC_TEXTURES = [
    ("smooth", "Smooth"),
    ("ribbed", "Ribbed"),
    ("tweed", "Tweed"),
    ("boucle", "Bouclé"),
    ("matte", "Matte"),
    ("glossy", "Glossy"),
    ("jacquard", "Jacquard"),
]

# Formal sub-categories (when Formal dress type is selected)
FORMAL_SUBCATEGORIES = [
    ("", "— Select sub-category —"),
    ("suits", "Suits"),
    ("shirts", "Shirts"),
    ("coats", "Coats"),
    ("jackets", "Jackets"),
    ("blazers", "Blazers"),
    ("trousers", "Trousers"),
    ("waistcoats", "Waistcoats"),
    ("overcoats", "Overcoats"),
]


def neworders_dresses_view(request):
    """
    New orders page for dresses — /neworders/dresses/
    Gate: viewers enter phone number to access designer list and dress types.
    """
    session_key = "neworder_dresses_phone"
    has_access = bool(request.session.get(session_key))

    if request.method == "POST":
        form = NewOrderAccessForm(request.POST)
        if form.is_valid():
            request.session[session_key] = form.cleaned_data["phone"]
            return redirect("neworders_dresses")
        # Form invalid: show gate with errors
        return render(
            request,
            "designer_portfolio/neworders_dresses.html",
            {"form": form, "has_access": False, "designers": [], "dress_types": DRESS_TYPES,
             "fabric_types": FABRIC_TYPES, "wool_types": WOOL_TYPES, "fabric_textures": FABRIC_TEXTURES,
             "formal_subcategories": FORMAL_SUBCATEGORIES},
        )

    if has_access:
        designers = (
            DesignerProfile.objects.filter(user__is_active=True)
            .select_related("user")
            .order_by("-created_at")[:50]
        )
        return render(
            request,
            "designer_portfolio/neworders_dresses.html",
            {
                "form": None,
                "has_access": True,
                "designers": designers,
                "dress_types": DRESS_TYPES,
                "fabric_types": FABRIC_TYPES,
                "wool_types": WOOL_TYPES,
                "fabric_textures": FABRIC_TEXTURES,
                "formal_subcategories": FORMAL_SUBCATEGORIES,
            },
        )

    return render(
        request,
        "designer_portfolio/neworders_dresses.html",
        {"form": NewOrderAccessForm(), "has_access": False, "designers": [], "dress_types": DRESS_TYPES,
         "fabric_types": FABRIC_TYPES, "wool_types": WOOL_TYPES, "fabric_textures": FABRIC_TEXTURES,
         "formal_subcategories": FORMAL_SUBCATEGORIES},
    )


def neworders_dresses_submit_view(request):
    """
    Submit a dress order to a designer. Requires session access (phone gate).
    Sends email notification to the designer and confirmation to the viewer.
    """
    session_key = "neworder_dresses_phone"
    if not request.session.get(session_key):
        messages.error(request, "Please enter your phone number to submit an order.")
        return redirect("neworders_dresses")

    if request.method != "POST":
        messages.error(request, "Invalid request.")
        return redirect("neworders_dresses")

    designer_id = request.POST.get("designer_id")
    if not designer_id:
        messages.error(request, "Please select a designer.")
        return redirect("neworders_dresses")

    try:
        designer = DesignerProfile.objects.get(
            user_id=int(designer_id),
            user__is_active=True,
        )
    except (DesignerProfile.DoesNotExist, ValueError, TypeError):
        messages.error(request, "Invalid designer selected.")
        return redirect("neworders_dresses")

    def _str(val):
        return (val or "").strip() if val is not None else ""

    def _decimal(val):
        if val is None or val == "":
            return None
        try:
            from decimal import Decimal
            return Decimal(str(val))
        except Exception:
            return None

    customer_email = _str(request.POST.get("customer_email"))
    if customer_email:
        try:
            validate_email(customer_email)
        except ValidationError:
            messages.error(
                request,
                "Please enter a valid email address to receive order confirmation.",
            )
            return redirect("neworders_dresses")

    order = DressOrder.objects.create(
        designer=designer,
        customer_phone=request.session.get(session_key, ""),
        customer_email=customer_email or "",
        status="new",
        dress_type=_str(request.POST.get("dress_type")),
        dress_label=_str(request.POST.get("dress_label")),
        shoulder_width=_decimal(request.POST.get("shoulder_width")),
        chest=_decimal(request.POST.get("chest")),
        sleeve_short=_decimal(request.POST.get("sleeve_short")),
        sleeve_wrist=_decimal(request.POST.get("sleeve_wrist")),
        fabric_type=_str(request.POST.get("fabric_type")),
        fabric_label=_str(request.POST.get("fabric_label")),
        wool_type=_str(request.POST.get("wool_type")),
        fabric_texture=_str(request.POST.get("fabric_texture")),
        formal_subcategory=_str(request.POST.get("formal_subcategory")),
    )

    viewer_confirmation_sent = False
    try:
        notify_designer_new_dress_order(order, request=request)
    except Exception:
        logger.exception("Failed to send dress order email to designer %s", designer_id)
    try:
        viewer_confirmation_sent = notify_viewer_dress_order_confirmation(
            order,
            viewer_email=customer_email,
            request=request,
        )
    except Exception:
        logger.exception("Failed to send dress order confirmation to viewer")

    designer_name = designer.user.get_full_name() or designer.user.username
    success_message = (
        f"Order sent to {designer_name}. They will receive an email notification and may contact you soon."
    )
    if viewer_confirmation_sent:
        success_message += " A confirmation email has also been sent to you."
    messages.success(
        request,
        success_message,
    )
    return redirect("neworders_dresses")


# ---------------- Designer Orders (Dress Orders) ----------------
@login_required
def designer_orders_list(request):
    """Designer sees their orders, filtered by status (default: new)."""
    profile = get_object_or_404(DesignerProfile, user=request.user)
    status_filter = (request.GET.get("status") or "new").strip()
    valid_statuses = [s[0] for s in DressOrder.STATUS_CHOICES]
    if status_filter not in valid_statuses:
        status_filter = "new"

    orders = (
        DressOrder.objects.filter(designer=profile)
        .select_related("design")
        .prefetch_related("updates")
        .filter(status=status_filter)
        .order_by("-created_at")
    )
    new_count = DressOrder.objects.filter(designer=profile, status="new").count()
    in_progress_count = DressOrder.objects.filter(designer=profile, status="in_progress").count()

    return render(
        request,
        "designer_portfolio/designer_orders_list.html",
        {
            "current_section": "orders",
            "orders": orders,
            "status_filter": status_filter,
            "new_count": new_count,
            "in_progress_count": in_progress_count,
            "new_orders_count": new_count,
        },
    )


@login_required
def designer_order_detail(request, order_id):
    """Designer sees order detail, can update status, add notes, attach design, add techpack."""
    profile = get_object_or_404(DesignerProfile, user=request.user)
    order = get_object_or_404(DressOrder, pk=order_id, designer=profile)
    order_updates = list(order.updates.order_by("created_at"))
    designer_designs = Design.objects.filter(designer=request.user).order_by("-created_at")

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "update_status":
            new_status = (request.POST.get("status") or "").strip()
            if new_status in dict(DressOrder.STATUS_CHOICES):
                order.status = new_status
                order.save(update_fields=["status"])
                notes = (request.POST.get("notes") or "").strip()
                if notes or new_status:
                    DressOrderUpdate.objects.create(
                        order=order,
                        status=new_status,
                        notes=notes,
                    )
                messages.success(request, f"Order status updated to {dict(DressOrder.STATUS_CHOICES).get(new_status, new_status)}.")
                return redirect("designer_order_detail", order_id=order.pk)
        elif action == "add_update":
            notes = (request.POST.get("notes") or "").strip()
            techpack_notes = (request.POST.get("techpack_notes") or "").strip()
            techpack_pdf = request.FILES.get("techpack_pdf")
            status_val = (request.POST.get("status") or "").strip() or order.status
            if notes or techpack_notes or techpack_pdf:
                update = DressOrderUpdate.objects.create(
                    order=order,
                    status=status_val,
                    notes=notes,
                    techpack_notes=techpack_notes,
                    techpack_pdf=techpack_pdf,
                )
                if status_val and status_val != order.status:
                    order.status = status_val
                    order.save(update_fields=["status"])
                messages.success(request, "Update added.")
                return redirect("designer_order_detail", order_id=order.pk)
            messages.error(request, "Please add notes or techpack information.")
        elif action == "attach_design":
            design_id = request.POST.get("design_id")
            if design_id:
                try:
                    design = Design.objects.get(pk=int(design_id), designer=request.user)
                    order.design = design
                    order.save(update_fields=["design"])
                    messages.success(request, f'Design "{design.title}" attached to this order.')
                    return redirect("designer_order_detail", order_id=order.pk)
                except (Design.DoesNotExist, ValueError, TypeError):
                    messages.error(request, "Invalid design selected.")
            else:
                order.design = None
                order.save(update_fields=["design"])
                messages.success(request, "Design detached from order.")
                return redirect("designer_order_detail", order_id=order.pk)

    new_orders_count = DressOrder.objects.filter(designer=profile, status="new").count()
    return render(
        request,
        "designer_portfolio/designer_order_detail.html",
        {
            "current_section": "orders",
            "order": order,
            "order_updates": order_updates,
            "designer_designs": designer_designs,
            "new_orders_count": new_orders_count,
            "status_choices": DressOrder.STATUS_CHOICES,
        },
    )


def viewer_order_detail(request, token):
    """Viewer sees their order (and linked design) via access token. No login required."""
    order = get_object_or_404(
        DressOrder.objects.prefetch_related("updates").select_related("design"),
        access_token=token,
    )
    return render(
        request,
        "designer_portfolio/viewer_order_detail.html",
        {"order": order},
    )


class AboutView(TemplateView):
    template_name = "designer_portfolio/about.html"

class AboutSiteView(TemplateView):
    template_name = "designer_portfolio/about_site.html"

class IPhoneAppDownloadView(TemplateView):
    template_name = "designer_portfolio/iphone_app_download.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        app_store_url = getattr(settings, "IOS_APP_STORE_URL", "").strip()
        testflight_url = getattr(settings, "IOS_TESTFLIGHT_URL", "").strip()
        play_store_url = getattr(settings, "ANDROID_PLAY_STORE_URL", "").strip()
        apk_url = getattr(settings, "ANDROID_APK_URL", "").strip()
        support_email = _get_public_contact_email()
        app_name = getattr(settings, "IOS_APP_NAME", "GlobalDesignerHub").strip() or "GlobalDesignerHub"

        def _link(label: str, url: str, icon: str, new_tab: bool = False) -> dict:
            payload = {"label": label, "url": url, "icon": icon}
            if new_tab:
                payload["target"] = "_blank"
                payload["rel"] = "noopener"
            return payload

        if app_store_url:
            primary_download = _link(
                "Download on the App Store",
                app_store_url,
                "fa-brands fa-apple",
                new_tab=True,
            )
            secondary_download = (
                _link("Join TestFlight", testflight_url, "fa-solid fa-rocket", new_tab=True)
                if testflight_url
                else _link("Email me the link", f"mailto:{support_email}", "fa-regular fa-envelope")
            )
        elif testflight_url:
            primary_download = _link("Join TestFlight", testflight_url, "fa-solid fa-rocket", new_tab=True)
            secondary_download = _link("Email me the link", f"mailto:{support_email}", "fa-regular fa-envelope")
        else:
            primary_download = _link(
                "Request the iPhone app",
                reverse("contact"),
                "fa-regular fa-paper-plane",
            )
            secondary_download = _link("Email support", f"mailto:{support_email}", "fa-regular fa-envelope")

        if play_store_url:
            android_primary = _link("Get it on Google Play", play_store_url, "fa-brands fa-google-play", new_tab=True)
            android_secondary = (
                _link("Download the APK", apk_url, "fa-brands fa-android", new_tab=True)
                if apk_url
                else _link("Email me the link", f"mailto:{support_email}", "fa-regular fa-envelope")
            )
        elif apk_url:
            android_primary = _link("Download the Android APK", apk_url, "fa-brands fa-android", new_tab=True)
            android_secondary = _link("Email me the link", f"mailto:{support_email}", "fa-regular fa-envelope")
        else:
            android_primary = _link(
                "Request the Android app",
                reverse("contact"),
                "fa-regular fa-paper-plane",
            )
            android_secondary = _link("Email support", f"mailto:{support_email}", "fa-regular fa-envelope")

        app_platforms = [
            {
                "name": "iPhone & iPad",
                "icon": "fa-brands fa-apple",
                "primary": primary_download,
                "secondary": secondary_download,
                "note": "Requires iOS 16 or later.",
            },
            {
                "name": "Android",
                "icon": "fa-brands fa-google-play",
                "primary": android_primary,
                "secondary": android_secondary,
                "note": "Requires Android 8.0 or later.",
            },
        ]

        context.update(
            {
                "app_name": app_name,
                "support_email": support_email,
                "primary_download": primary_download,
                "secondary_download": secondary_download,
                "android_primary": android_primary,
                "android_secondary": android_secondary,
                "app_platforms": app_platforms,
                "app_hero_points": [
                    "Review tech packs and approve updates on the go.",
                    "Message designers with secure threads and shared files.",
                    "Stay on schedule with collection and event alerts.",
                ],
                "app_feature_cards": [
                    {
                        "title": "Portfolio access",
                        "description": "Open lookbooks, tech packs, and collections from your iPhone.",
                        "icon": "fa-solid fa-layer-group",
                    },
                    {
                        "title": "Mobile uploads",
                        "description": "Capture studio progress shots and attach them to active projects.",
                        "icon": "fa-solid fa-camera-retro",
                    },
                    {
                        "title": "Instant messaging",
                        "description": "Keep conversations moving with in-app chat and notifications.",
                        "icon": "fa-regular fa-comments",
                    },
                    {
                        "title": "Event reminders",
                        "description": "Track fashion week schedules and community meetups in one place.",
                        "icon": "fa-regular fa-calendar-days",
                    },
                ],
                "app_download_steps": [
                    {
                        "title": "Download the app",
                        "description": f"Install {app_name} from the App Store or TestFlight using the button above.",
                    },
                    {
                        "title": "Sign in securely",
                        "description": f"Use your existing {app_name} account or create one in minutes.",
                    },
                    {
                        "title": "Enable alerts",
                        "description": "Get real-time updates for approvals, messages, and events.",
                    },
                ],
            }
        )
        return context

def contact_view(request):
    contact_email = _get_public_contact_email()
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            subject = f"[GlobalDesignerHub] Contact request: {data['subject']}"
            body = (
                "A new contact form submission was received on globaldesignerhub.com/contact\n\n"
                f"Name: {data['name']}\n"
                f"Email: {data['email']}\n"
                f"Subject: {data['subject']}\n\n"
                f"Message:\n{data['message']}\n"
            )
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@globaldesignerhub.com"),
                to=[contact_email],
                reply_to=[data["email"]],
            )
            try:
                email.send(fail_silently=False)
            except BadHeaderError:
                messages.error(request, "Invalid header detected. Please email us directly instead.")
            except Exception:
                logger.exception("Contact form email failed")
                messages.error(
                    request,
                    f"We couldn't send your message right now. Email {contact_email} while we investigate.",
                )
            else:
                messages.success(request, "Thanks for reaching out. Our studio will reply shortly.")
                return redirect("contact")
    else:
        form = ContactForm()

    return render(
        request,
        "designer_portfolio/contact.html",
        {
            "form": form,
            "contact_email": contact_email,
        },
    )


def students_landing_view(request):
    """Landing page for design students — /students. Optionally shown as popup via ?popup=1."""
    contact_email = _get_public_contact_email()
    form = StudentInviteRequestForm()

    if request.method == "POST":
        form = StudentInviteRequestForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            subject = "[GlobalDesignerHub] Student invite request"
            body = (
                "New student invite request from globaldesignerhub.com/students\n\n"
                f"Name: {data['name']}\n"
                f"Email: {data['email']}\n"
                f"College/Program: {data.get('college') or '(not provided)'}\n"
            )
            email = EmailMessage(
                subject=subject,
                body=body,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@globaldesignerhub.com"),
                to=[contact_email],
                reply_to=[data["email"]],
            )
            try:
                email.send(fail_silently=False)
            except BadHeaderError:
                messages.error(request, "Invalid header detected. Please try again or email us directly.")
            except Exception:
                logger.exception("Student invite request email failed")
                messages.error(
                    request,
                    f"We couldn't process your request right now. Email {contact_email} while we investigate.",
                )
            else:
                messages.success(
                    request,
                    "Thanks! We've received your details. Our team will set up your portfolio and reach out soon.",
                )
                return redirect("students")
        else:
            messages.error(request, "Please correct the errors below.")

    return render(
        request,
        "designer_portfolio/students.html",
        {
            "form": form,
            "contact_email": contact_email,
            "show_as_popup": request.GET.get("popup") == "1",
        },
    )


def invite_view(request, code: str):
    """Capture referral code in session and redirect to signup. No DB write on click."""
    request.session["referral_code"] = code.strip().lower()
    request.session["referral_source"] = request.GET.get("source", "").strip() or None
    return redirect(reverse("signup"))


class GlobalDesignerHubLegalPageView(TemplateView):
    """
    Shared base view so every legal/policy page exposes the same company data.
    """

    company_name = "GlobalDesignerHub"
    effective_date = "December 1, 2025"
    company_location = "Saratoga, CA – USA – 95070"
    service_brands = ("GlobalDesignerHub", "TailorHub", "VolumeOne")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact_email = (
            getattr(settings, "GLOBALDESIGNERHUB_CONTACT_EMAIL", "")
            or getattr(settings, "PRETTYPEARL_CONTACT_EMAIL", "")
            or getattr(settings, "ADMIN_EMAIL", "")
            or "support@globaldesignerhub.com"
        )
        context.update(
            {
                "company_name": self.company_name,
                "effective_date": self.effective_date,
                "contact_email": contact_email,
                "company_location": self.company_location,
                "service_brands": self.service_brands,
            }
        )
        return context


class PrivacyPolicyView(GlobalDesignerHubLegalPageView):
    template_name = "designer_portfolio/privacy_policy.html"


class TermsOfServiceView(GlobalDesignerHubLegalPageView):
    template_name = "designer_portfolio/terms_of_service.html"


class RefundPolicyView(GlobalDesignerHubLegalPageView):
    template_name = "designer_portfolio/refund_policy.html"


class GrievancePolicyView(GlobalDesignerHubLegalPageView):
    template_name = "designer_portfolio/grievance_policy.html"


class DataRightsPolicyView(GlobalDesignerHubLegalPageView):
    template_name = "designer_portfolio/data_rights_policy.html"


class AccessibilityStatementView(GlobalDesignerHubLegalPageView):
    template_name = "designer_portfolio/accessibility_statement.html"


class SecurityPolicyView(GlobalDesignerHubLegalPageView):
    template_name = "designer_portfolio/security_policy.html"


class ReportProblemView(FormView):
    template_name = "designer_portfolio/report_problem.html"
    form_class = ReportProblemForm
    success_url = reverse_lazy("report_problem_thanks")

    def get_initial(self):
        initial = super().get_initial()
        user = self.request.user
        if user.is_authenticated:
            initial.setdefault("name", user.get_full_name() or user.get_username())
            if user.email:
                initial.setdefault("email", user.email)
        page_hint = (self.request.GET.get("page") or "").strip()
        if page_hint:
            initial.setdefault("page_url", page_hint)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["support_email"] = (
            getattr(settings, "PRETTYPEARL_CONTACT_EMAIL", "")
            or getattr(settings, "ADMIN_EMAIL", "")
            or "support@globaldesignerhub.com"
        )
        context["category_cards"] = [
            {
                "key": ProblemReport.CATEGORY_WEBSITE,
                "title": "Website improvements",
                "description": "Navigation confusion, missing content, or layout fixes.",
                "icon": "fa-solid fa-sparkles",
            },
            {
                "key": ProblemReport.CATEGORY_TECHNICAL,
                "title": "Technical issues",
                "description": "Errors, performance hiccups, sign-in or upload failures.",
                "icon": "fa-solid fa-bug",
            },
            {
                "key": ProblemReport.CATEGORY_BILLING,
                "title": "Billing & subscriptions",
                "description": "Plan upgrades, invoices, credit card or PayPal problems.",
                "icon": "fa-solid fa-credit-card",
            },
            {
                "key": ProblemReport.CATEGORY_OTHER,
                "title": "Something else",
                "description": "Anything that doesn't fit above — we still want to know.",
                "icon": "fa-solid fa-comments",
            },
        ]
        return context

    def form_valid(self, form):
        report: ProblemReport = form.save(commit=False)
        request = self.request
        if request.user.is_authenticated:
            report.reporter = request.user
            if not report.email:
                report.email = (request.user.email or "").strip()
            if not report.name:
                report.name = request.user.get_full_name() or request.user.get_username()

        report.ip_address = request.META.get("REMOTE_ADDR") or None
        report.user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:500]
        report.save()

        transaction.on_commit(lambda: notify_problem_report(report, request=request))

        if _request_wants_json(request):
            return JsonResponse(
                {
                    "status": "ok",
                    "report_id": report.pk,
                }
            )

        messages.success(request, "Thanks for sharing — our team will review your report shortly.")
        return super().form_valid(form)

    def form_invalid(self, form):
        if _request_wants_json(self.request):
            return JsonResponse({"errors": form.errors}, status=400)
        return super().form_invalid(form)


class ReportProblemThanksView(TemplateView):
    template_name = "designer_portfolio/report_problem_thanks.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["support_email"] = (
            getattr(settings, "PRETTYPEARL_CONTACT_EMAIL", "")
            or getattr(settings, "ADMIN_EMAIL", "")
            or "support@globaldesignerhub.com"
        )
        return context


class CommunityForumView(TemplateView):
    template_name = "designer_portfolio/community_forum.html"

    FAQ_FILTERS = [
        {
            "key": "onboarding",
            "label": "Getting Started",
            "description": "Access, verification, and posting basics.",
            "icon": "fa-solid fa-rocket",
        },
        {
            "key": "design_workflows",
            "label": "Design Workflows",
            "description": "Uploads, tech packs, and milestones.",
            "icon": "fa-solid fa-pen-ruler",
        },
        {
            "key": "collaboration",
            "label": "Collaboration",
            "description": "Share links, reviews, and feedback loops.",
            "icon": "fa-solid fa-people-group",
        },
        {
            "key": "subscriptions",
            "label": "Subscriptions",
            "description": "Billing, seats, and plan changes.",
            "icon": "fa-solid fa-credit-card",
        },
        {
            "key": "events",
            "label": "Events",
            "description": "AMAs, program calendar, and replays.",
            "icon": "fa-solid fa-calendar-days",
        },
        {
            "key": "ai_tools",
            "label": "AI Co-Designer",
            "description": "Designer AI prompts and workflows.",
            "icon": "fa-solid fa-robot",
        },
        {
            "key": "support",
            "label": "Support & Trust",
            "description": "Reporting abuse and urgent escalation.",
            "icon": "fa-solid fa-shield",
        },
    ]

    FAQ_ENTRIES = [
        {
            "question": "Who can join the GlobalDesignerHub Community Forum?",
            "answer": (
                "Every active designer account automatically gains forum access with the same "
                "GlobalDesignerHub credentials. If your portfolio is still pending approval, you can browse "
                "read-only threads while the trust & safety team finalizes verification. Brand partners can be "
                "invited by an approved designer via the Community > Invite Partner flow from the dashboard."
            ),
            "category": "onboarding",
            "tags": ["access", "eligibility", "partners"],
            "updated": "Nov 2025",
        },
        {
            "question": "How should I prep my profile before posting in a community topic?",
            "answer": (
                "Complete the Designer Dashboard > About Me section so your bio, region, and specialties show "
                "up next to every post. Threads that link to at least one published design or collection receive "
                "priority in the ‘Top Work-In-Progress’ feed, so publish at least one design first."
            ),
            "category": "onboarding",
            "tags": ["profile", "dashboard", "visibility"],
            "updated": "Nov 2025",
        },
        {
            "question": "What qualifies as a complete design upload when I request critique?",
            "answer": (
                "A critique-ready post should include: the design slug (copied from the design detail page), "
                "at least one cover image, a short goal statement, and any tech pack files you are comfortable "
                "sharing. Community moderators flag posts missing visuals so please upload via Designs > Upload Design beforehand."
            ),
            "category": "design_workflows",
            "tags": ["design upload", "tech pack", "feedback"],
            "updated": "Nov 2025",
        },
        {
            "question": "Can I invite a brand partner or mentor into a private feedback thread?",
            "answer": (
                "Yes. Create a private feedback channel from the thread action menu, then add any verified "
                "GlobalDesignerHub email or send a one-time guest link that expires in 7 days. Guests can comment, "
                "annotate images, and leave timestamped notes but cannot see unpublished designs outside the thread."
            ),
            "category": "collaboration",
            "tags": ["feedback", "guests", "sharing"],
            "updated": "Oct 2025",
        },
        {
            "question": "Is forum access included in my subscription and what about archived teams?",
            "answer": (
                "All paid and trial GlobalDesignerHub subscriptions include full forum participation. If your "
                "subscription lapses, you retain read-only access for 30 days so you can export any bookmarked "
                "threads before the workspace is archived. Re-subscribe at any time to reopen posting privileges."
            ),
            "category": "subscriptions",
            "tags": ["billing", "plans", "access"],
            "updated": "Sep 2025",
        },
        {
            "question": "Where do I find community AMAs, challenges, and event replays?",
            "answer": (
                "Open Events in the main navigation for upcoming sessions, then visit the pinned ‘Event Recaps’ "
                "collection inside the forum to watch recordings, download decks, and follow challenge rules. "
                "Each event thread includes filters for format (AMA, workshop, call for entries) and deadlines."
            ),
            "category": "events",
            "tags": ["calendar", "replay", "challenges"],
            "updated": "Oct 2025",
        },
        {
            "question": "How does the Designer AI assistant support threads inside the forum?",
            "answer": (
                "You can highlight any message and choose “Summarize with Designer AI” to receive a brief, "
                "attributed recap. The assistant also suggests follow-up prompts based on your portfolio data "
                "and can draft replies from the Designer AI Chat widget embedded on the right rail."
            ),
            "category": "ai_tools",
            "tags": ["ai", "summaries", "automation"],
            "updated": "Nov 2025",
        },
        {
            "question": "How do I escalate urgent issues or report abuse in the community?",
            "answer": (
                "Use the Flag option on any post to alert moderators within minutes. For urgent safety or IP "
                "concerns, email support@globaldesignerhub.com with links to the affected threads. We maintain a "
                "24/7 incident channel and will update you within one business day."
            ),
            "category": "support",
            "tags": ["safety", "moderation", "abuse reports"],
            "updated": "Always on",
        },
    ]

    def _build_filter_url(self, topic_key: str, search_query: str) -> str:
        normalized_topic = (topic_key or "").strip()
        normalized_query = (search_query or "").strip()
        params = {}
        if normalized_topic and normalized_topic != "all":
            params["topic"] = normalized_topic
        if normalized_query:
            params["q"] = normalized_query
        query_string = urlencode(params)
        return f"{self.request.path}?{query_string}" if query_string else self.request.path

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        forum_url = getattr(
            settings,
            "COMMUNITY_FORUM_URL",
            "https://community.globaldesignerhub.com",
        )

        search_query = (self.request.GET.get("q") or "").strip()
        active_filter = (self.request.GET.get("topic") or "all").strip() or "all"
        valid_categories = {item["key"] for item in self.FAQ_FILTERS}
        if active_filter != "all" and active_filter not in valid_categories:
            active_filter = "all"

        filter_items = []
        for item in self.FAQ_FILTERS:
            item_copy = item.copy()
            item_copy["url"] = self._build_filter_url(item["key"], search_query)
            item_copy["is_active"] = item["key"] == active_filter
            filter_items.append(item_copy)

        category_lookup = {item["key"]: item for item in filter_items}
        faq_entries = []
        has_visible_faqs = False
        search_query_lower = search_query.lower()

        for idx, entry in enumerate(self.FAQ_ENTRIES):
            enriched_entry = entry.copy()
            category_meta = category_lookup.get(entry["category"], {}) or {
                "label": entry["category"].replace("_", " ").title(),
                "icon": "fa-solid fa-circle",
            }
            enriched_entry["category_label"] = category_meta.get(
                "label", entry["category"].replace("_", " ").title()
            )
            enriched_entry["category_icon"] = category_meta.get(
                "icon", "fa-solid fa-circle"
            )
            tags = entry.get("tags", [])
            enriched_entry["tags"] = tags
            search_components = [
                enriched_entry["question"],
                enriched_entry["answer"],
                " ".join(tags),
                enriched_entry["category_label"],
            ]
            search_blob = " ".join(filter(None, search_components))
            matches_filter = active_filter == "all" or entry["category"] == active_filter
            matches_search = not search_query_lower or search_query_lower in search_blob.lower()
            should_show = matches_filter and matches_search
            has_visible_faqs = has_visible_faqs or should_show
            safe_slug = slugify(entry["question"]) or f"{entry['category']}-{idx}"
            enriched_entry["html_id"] = f"faq-{safe_slug}"
            enriched_entry["search_blob"] = search_blob
            enriched_entry["should_show"] = should_show
            faq_entries.append(enriched_entry)

        context.update(
            {
                "community_forum_url": forum_url,
                "faq_filters": filter_items,
                "faq_entries": faq_entries,
                "active_faq_filter": active_filter,
                "search_query": search_query,
                "all_filter_url": self._build_filter_url("all", search_query),
                "has_visible_faqs": has_visible_faqs,
            }
        )
        return context


def docs_index(request, category_slug=None):
    """
    Render documentation index or category-specific listing.
    """

    categories = _doc_categories_with_counts()
    slug_to_value = {category["slug"]: category["value"] for category in categories}

    docs_queryset = DocPage.objects.filter(published=True).order_by("order", "title")
    active_category = None
    active_category_label = None

    if category_slug:
        category_value = slug_to_value.get(category_slug)
        if category_value is None:
            raise Http404("Documentation category not found.")
        docs_queryset = _filter_docs_by_category(docs_queryset, category_value)
        active_category = category_slug
        _, active_category_label, _ = _doc_category_parts(category_value)

    context = {
        "categories": categories,
        "active_category": active_category,
        "active_category_label": active_category_label,
        "docs": list(docs_queryset),
    }
    return render(request, "designer_portfolio/docs_index.html", context)


def docs_detail(request, category_slug, doc_slug):
    """
    Render a single documentation page with related links.
    """

    doc = get_object_or_404(DocPage, slug=doc_slug, published=True)
    _, category_label, doc_category_slug = _doc_category_parts(doc.category)

    if doc_category_slug != category_slug:
        raise Http404("Documentation page not found.")

    categories = _doc_categories_with_counts()
    related_docs = (
        _filter_docs_by_category(DocPage.objects.filter(published=True).exclude(pk=doc.pk), doc.category)
        .order_by("order", "title")[:5]
    )

    context = {
        "doc": doc,
        "category_label": category_label,
        "categories": categories,
        "related_docs": related_docs,
        "active_category": doc_category_slug,
    }
    return render(request, "designer_portfolio/docs_detail.html", context)

class CollectionsPageView(TemplateView):
    template_name = "designer_portfolio/collections.html"
    guest_link_expiry_days = RUNWAY_GUEST_LINK_EXPIRY_DAYS
    SORT_MAP = {
        "newest": "-year",
        "oldest": "year",
        "name": "name",
        "season": "season",
    }

    def _resolve_view_mode(self) -> str:
        view_mode = (self.request.GET.get("view") or "").lower()
        return "list" if view_mode == "list" else "grid"

    def _resolve_sort(self):
        requested = (self.request.GET.get("sort") or "newest").lower()
        sort_field = self.SORT_MAP.get(requested, "-year")
        return requested if requested in self.SORT_MAP else "newest", sort_field

    def _can_view_private(self) -> bool:
        user = getattr(self.request, "user", None)
        return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))

    def _build_querystring(self, **overrides) -> str:
        params = self.request.GET.copy()
        for key, value in overrides.items():
            if not value:
                if key in params:
                    del params[key]
            else:
                params[key] = value
        encoded = params.urlencode()
        return f"?{encoded}" if encoded else ""

    def get_queryset(self):
        queryset = Collection.objects.prefetch_related("gallery", "looks")
        if not self._can_view_private():
            queryset = queryset.filter(published=True)
        return queryset

    def _collection_metrics(self, payloads) -> dict:
        total = len(payloads)
        lookbook_entries = sum(item["look_count"] for item in payloads)
        techpack_ready = sum(1 for item in payloads if item["attachment_count"])
        motion_ready = sum(1 for item in payloads if item["has_motion"])
        public_rows = sum(1 for item in payloads if item["published"])
        return {
            "total_collections": total,
            "public_collections": public_rows,
            "lookbook_entries": lookbook_entries,
            "techpack_ready": techpack_ready,
            "motion_enabled": motion_ready,
        }

    def _private_collection_count(self, allow_lookup: bool) -> int:
        if not allow_lookup:
            return 0
        try:
            return Collection.objects.filter(published=False).count()
        except Exception:
            return 0

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        placeholder = static("images/placehold.png")
        view_mode = self._resolve_view_mode()
        sort_key, sort_field = self._resolve_sort()
        can_view_private = self._can_view_private()

        try:
            queryset = self.get_queryset().order_by(sort_field, "name")
            collections_payload = [
                build_runway_collection_payload(
                    collection,
                    placeholder_url=placeholder,
                    guest_link_days=self.guest_link_expiry_days,
                )
                for collection in queryset
            ]
        except Exception as exc:
            logger.exception("Failed to load collections list", exc_info=exc)
            collections_payload = []
            context["collections_error"] = (
                "Runway collections are temporarily unavailable. Refresh to try again."
            )

        context.update(
            {
                "collections_payload": collections_payload,
                "collection_placeholder": placeholder,
                "runway_capabilities": RUNWAY_COLLECTION_CAPABILITIES,
                "view_mode": view_mode,
                "active_sort": sort_key,
                "sort_options": [
                    {"value": "newest", "label": "Newest first", "active": sort_key == "newest"},
                    {"value": "oldest", "label": "Oldest first", "active": sort_key == "oldest"},
                    {"value": "name", "label": "Designer A→Z", "active": sort_key == "name"},
                    {"value": "season", "label": "Season", "active": sort_key == "season"},
                ],
                "view_toggle_links": {
                    "grid": self._build_querystring(view="grid"),
                    "list": self._build_querystring(view="list"),
                },
                "collection_metrics": self._collection_metrics(collections_payload),
                "guest_link_expiry_days": self.guest_link_expiry_days,
                "can_view_private": can_view_private,
                "private_collection_count": self._private_collection_count(can_view_private),
                "list_view_available": bool(collections_payload),
                "list_view_is_public": True,
                "audience_explainer": {
                    "viewer": "Grid and list view cards for published collections are visible to every visitor.",
                    "designer": "Sign in to surface draft or private review collections plus attachment controls.",
                },
            }
        )

        return context


class CollectionDetailView(DetailView):
    template_name = "designer_portfolio/collection_detail.html"
    model = Collection
    context_object_name = "collection"
    slug_url_kwarg = "slug"
    guest_link_expiry_days = RUNWAY_GUEST_LINK_EXPIRY_DAYS

    def get_queryset(self):
        queryset = Collection.objects.prefetch_related("gallery", "looks")
        if not (self.request.user.is_authenticated and self.request.user.is_staff):
            queryset = queryset.filter(published=True)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        placeholder = static("images/placehold.png")
        payload = build_runway_collection_payload(
            context["collection"],
            placeholder_url=placeholder,
            guest_link_days=self.guest_link_expiry_days,
        )
        context.update(
            {
                "runway_collection": payload,
                "media": payload["media"],
                "lookbook": payload["lookbook"],
                "lookbook_version": payload["lookbook_version"],
                "guest_link_expiry_days": self.guest_link_expiry_days,
                "runway_capabilities": RUNWAY_COLLECTION_CAPABILITIES,
                "collection_placeholder": placeholder,
            }
        )
        return context

class DesignListView(TemplateView):
    template_name = "designer_portfolio/designs.html"

class DesignDetailView(DetailView):
    model = Design
    template_name = "designer_portfolio/design_detail.html"
    context_object_name = "collection"  # Template expects collection/media structure
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Design.objects.prefetch_related("images")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        design = self.object
        # If design is linked to an order, only designer and order viewer can see it
        if design.dress_orders.exists():
            can_view = False
            if request.user.is_authenticated and design.designer_id == request.user.pk:
                can_view = True
            token = (request.GET.get("token") or "").strip()
            if token and design.dress_orders.filter(access_token=token).exists():
                can_view = True
            if not can_view:
                raise Http404("Design not found")
        elif not design.published:
            # Unpublished design not linked to order: only designer can see
            if not request.user.is_authenticated or design.designer_id != request.user.pk:
                raise Http404("Design not found")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        design = self.object
        # Build collection-like structure for template (title, year, text, media)
        from django.templatetags.static import static
        media = []
        for img in design.images.order_by("order"):
            if img.image:
                media.append({"type": "image", "url": img.image.url, "name": img.caption or design.title})
        if not media and design.cover_image:
            media.append({"type": "image", "url": design.cover_image.url, "name": design.title})
        context["collection"] = {
            "title": design.title,
            "year": design.year,
            "text": [design.description] if design.description else [],
        }
        context["media"] = media
        return context

def _build_event_media(event: Event) -> list[dict[str, str]]:
    media = []
    for image in event.images.all():
        if not image.image:
            continue
        media.append(
            {
                "type": "image",
                "url": image.image.url,
                "name": image.caption or event.title,
            }
        )
    if not media and event.cover:
        media.append({"type": "image", "url": event.cover.url, "name": event.title})
    return media


class EventListView(ListView):
    template_name = "designer_portfolio/events.html"
    context_object_name = "events"
    model = Event

    def get_queryset(self):
        return Event.objects.prefetch_related("images").all()


class EventDetailView(DetailView):
    template_name = "designer_portfolio/event_detail.html"
    model = Event
    context_object_name = "event"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        return Event.objects.prefetch_related(
            "images",
            "attendees",
            "collaboration_requests",
        )

    def get_context_data(self, **kwargs):
        attendee_form = kwargs.pop("attendee_form", None) or EventAttendeeForm()
        collaboration_form = kwargs.pop("collaboration_form", None) or EventCollaborationForm()

        context = super().get_context_data(**kwargs)
        event = context["event"]
        attendee_count = event.attendees.count()
        collaboration_count = event.collaboration_requests.count()
        seats_remaining = None
        if event.attendee_capacity:
            seats_remaining = max(event.attendee_capacity - attendee_count, 0)

        context.update(
            {
                "media": _build_event_media(event),
                "attendee_form": attendee_form,
                "collaboration_form": collaboration_form,
                "attendee_count": attendee_count,
                "collaboration_count": collaboration_count,
                "seats_remaining": seats_remaining,
                "recent_attendees": event.attendees.order_by("-created_at")[:6],
                "recent_collaborations": event.collaboration_requests.order_by("-created_at")[:6],
                "is_newyork_event": event.slug in {"newyork-fashion-show", "new-york-fashion-show"},
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_type = (request.POST.get("form_type") or "").strip()

        if form_type == "attendee":
            if not request.user.is_authenticated:
                messages.error(
                    request,
                    "Please sign in to RSVP. Only registered GlobalDesignerHub users can register for shows.",
                )
                return redirect("event_detail", slug=self.object.slug)
            attendee_form = EventAttendeeForm(request.POST)
            if attendee_form.is_valid():
                attendee = attendee_form.save(commit=False)
                attendee.event = self.object
                try:
                    attendee.save()
                except IntegrityError:
                    messages.info(
                        request,
                        "You're already registered for this event. We'll keep you on the list.",
                    )
                else:
                    location_label = self.object.location or "the show"
                    messages.success(
                        request,
                        f"RSVP received. We'll see you at {location_label}.",
                    )
                    return redirect("event_detail", slug=self.object.slug)
            context = self.get_context_data(attendee_form=attendee_form)
            return self.render_to_response(context)

        if form_type == "collaboration":
            collaboration_form = EventCollaborationForm(request.POST)
            if collaboration_form.is_valid():
                collaboration = collaboration_form.save(commit=False)
                collaboration.event = self.object
                try:
                    collaboration.save()
                except IntegrityError:
                    messages.info(
                        request,
                        "We already have a collaboration request for this email.",
                    )
                else:
                    messages.success(
                        request,
                        "Thanks for reaching out. We'll review your collaboration request shortly.",
                    )
                    return redirect("event_detail", slug=self.object.slug)
            context = self.get_context_data(collaboration_form=collaboration_form)
            return self.render_to_response(context)

        messages.error(request, "Please choose a form to submit.")
        return redirect("event_detail", slug=self.object.slug)
class DesignerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "designer_portfolio/designer_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Simplified dashboard to avoid potential issues
        try:
            user_designs_qs = Design.objects.filter(designer=user).order_by("-created_at")
            recent_designs = list(user_designs_qs[:8])
            total_designs = user_designs_qs.count()
        except Exception as e:
            # Fallback if there's an issue with Design model
            recent_designs = []
            total_designs = 0

        try:
            total_collections = Collection.objects.count()
        except Exception as e:
            total_collections = 0

        try:
            total_events = Event.objects.count()
        except Exception as e:
            total_events = 0

        try:
            recent_collections = list(Collection.objects.order_by("-year", "name")[:5])
        except Exception as e:
            recent_collections = []

        context.update(
            {
                "current_section": "dashboard",
                "total_designs": total_designs,
                "total_collections": total_collections,
                "total_events": total_events,
                "user_designs": recent_designs,
                "recent_designs": recent_designs,
                "recent_collections": recent_collections,
            }
        )

        return context


class ProjectTemplateSelectionView(LoginRequiredMixin, TemplateView):
    template_name = "designer_portfolio/project_new.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        templates = load_project_templates()
        default_template = templates[0] if templates else {}
        form = ProjectCreateForm(
            initial={
                "product_type": Project.ProductType.HOODIE,
                "product_count": 1,
            }
        )
        context.update(
            {
                "current_section": "projects",
                "project_templates": templates,
                "project_templates_json": serialize_templates_for_client(),
                "project_form": form,
                "default_template_id": default_template.get("id"),
                "season_choices": Project.SeasonChoices.choices,
                "product_type_choices": Project.ProductType.choices,
            }
        )
        try:
            context.setdefault("total_designs", Design.objects.filter(designer=self.request.user).count())
        except Exception:
            context.setdefault("total_designs", 0)
        return context


class ProjectEditorView(LoginRequiredMixin, DetailView):
    template_name = "designer_portfolio/project_editor.html"
    model = Project
    context_object_name = "project"

    def get_queryset(self):
        return (
            Project.objects.filter(owner=self.request.user)
            .prefetch_related("stages__bullets", "product_specs__fields")
            .order_by("-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_section"] = "projects"
        try:
            context.setdefault("total_designs", Design.objects.filter(designer=self.request.user).count())
        except Exception:
            context.setdefault("total_designs", 0)
        return context


class VolumeOneView(LoginRequiredMixin, TemplateView):
    template_name = "designer_portfolio/volume_one.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_section"] = "volume_one"
        try:
            context.setdefault("total_designs", Design.objects.filter(designer=self.request.user).count())
        except Exception:
            context.setdefault("total_designs", 0)
        try:
            public_url = reverse("volume_one_public")
        except NoReverseMatch:
            public_url = "/volumeone/"
        context["volume_one_url"] = self.request.build_absolute_uri(public_url)
        return context


class VolumeOneShowcaseView(TemplateView):
    template_name = "designer_portfolio/volume_one_public.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        feed = get_volumeone_feed()
        context.update(
            {
                "feed_profile": feed.get("profile", {}),
                "slides": feed.get("slides", []),
                "feed_source": feed.get("source", "fallback"),
                "feed_timestamp": feed.get("fetched_at"),
                "instagram_profile_url": _gdh_instagram_profile_url(),
                "instagram_username": VOLUMEONE_INSTAGRAM_USERNAME,
                "design_packs": _get_volumeone_design_packs(),
                "db_schema_tables": VOLUMEONE_DB_SCHEMA,
                "template_library": VOLUMEONE_TEMPLATE_LIBRARY,
            }
        )
        return context


@login_required
def project_templates_api(request):
    return JsonResponse({"templates": load_project_templates()})


@login_required
@require_POST
def create_project_api(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (AttributeError, ValueError, UnicodeDecodeError):
        payload = request.POST.dict()

    normalized = {
        "template_id": payload.get("templateId") or payload.get("template_id"),
        "title": payload.get("title") or payload.get("projectTitle"),
        "subtitle": payload.get("subtitle") or payload.get("coverSubtitle"),
        "client_name": payload.get("clientName") or payload.get("client_name"),
        "season": payload.get("season"),
        "product_type": payload.get("productType") or payload.get("product_type"),
        "product_count": payload.get("productCount") or payload.get("product_count") or 1,
    }

    form = ProjectCreateForm(normalized)
    if not form.is_valid():
        error_data = {
            field: [message["message"] for message in messages]
            for field, messages in form.errors.get_json_data().items()
        }
        return JsonResponse({"errors": error_data}, status=400)

    template_instance = form.template_instance
    template_definition = copy.deepcopy(form.template_data)
    summary_lines = template_definition.get("summary") or PROJECT_TEMPLATE_DEFAULT_SUMMARY
    cover_snapshot = template_definition.get("cover") or {}

    with transaction.atomic():
        project = Project.objects.create(
            owner=request.user,
            template_id=template_instance.id if template_instance else form.cleaned_data["template_id"],
            template_name=template_definition.get("name") or (template_instance.name if template_instance else form.cleaned_data["template_id"]) or "Template",
            template_category=template_definition.get("category", ""),
            template_layout_key=template_definition.get("layoutKey", ""),
            template_snapshot=template_definition,
            title=form.cleaned_data["title"],
            subtitle=form.cleaned_data.get("subtitle")
            or cover_snapshot.get("subtitle")
            or cover_snapshot.get("subtitlePlaceholder")
            or "",
            client_name=form.cleaned_data.get("client_name", ""),
            season=form.cleaned_data.get("season", ""),
            product_type=form.cleaned_data["product_type"],
            product_count=form.cleaned_data["product_count"],
            preview_copy=summary_lines,
            metadata={
                "cover": cover_snapshot,
                "thumbnail": template_definition.get("thumbnail", {}),
                "subtitle": form.cleaned_data.get("subtitle")
                or cover_snapshot.get("subtitle")
                or cover_snapshot.get("subtitlePlaceholder")
                or "",
            },
        )
        _copy_template_blueprint(project, template_instance or template_definition, snapshot=template_definition)

    created_iso = project.created_at.astimezone(dt_timezone.utc).isoformat().replace("+00:00", "Z")
    response_payload = {
        "id": project.pk,
        "templateId": project.template_id,
        "title": project.title,
        "subtitle": project.subtitle,
        "clientName": project.client_name,
        "season": project.season,
        "productType": project.product_type,
        "createdAt": created_iso,
        "redirectUrl": reverse("project_editor", args=[project.pk]),
        "message": "Project created.",
    }
    return JsonResponse(response_payload, status=201)

class PendingDesignersView(ListView):
    template_name = "designer_portfolio/pending_designers.html"

# ViewSets (minimal)
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated

class BrandViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response([])

class CollectionViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response([])

class DesignViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response([])

class EventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Event.objects.prefetch_related("images").all()
    serializer_class = EventSerializer

# ---- API: Designer Registration ----
class DesignerRegistrationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        data = getattr(request, "data", {}) or {}
        recaptcha_token = (
            (data.get("g-recaptcha-response") or data.get("recaptcha_token") or "").strip()
        )
        recaptcha_ok, recaptcha_error = verify_recaptcha_token(
            recaptcha_token, remote_ip=request.META.get("REMOTE_ADDR")
        )
        if not recaptcha_ok:
            return Response(
                {"errors": {"recaptcha": recaptcha_error}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        website_url = (data.get("website_url") or data.get("portfolio_website") or "").strip()
        subscription_plan = (data.get("subscription_plan") or "").strip()
        payment_method = (data.get("payment_method") or "").strip()

        # If a previously registered but inactive user exists, restore their account
        if email or username:
            inactive_user = (
                User.objects.filter(
                    Q(is_active=False), Q(username__iexact=username) | Q(email__iexact=email)
                )
                .order_by("id")
                .first()
            )
            if inactive_user is not None:
                errors = {}
                if not password:
                    errors["password"] = "This field is required."
                else:
                    try:
                        validate_password(password, user=inactive_user)
                    except ValidationError as exc:
                        errors["password"] = list(exc.messages)

                if errors:
                    return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

                inactive_user.is_active = True
                if email:
                    inactive_user.email = email
                inactive_user.set_password(password)
                inactive_user.save()

                # Ensure related records
                ensure_designer_access(inactive_user)
                profile = inactive_user.designer_profile
                if website_url:
                    try:
                        URLValidator()(website_url)
                        profile.portfolio_website = website_url
                        profile.save()
                    except ValidationError:
                        pass

                ref_code = data.get("referral_code") or request.session.pop("referral_code", None)
                ref_source = data.get("referral_source") or request.session.pop("referral_source", None)
                try:
                    from .services.referrals import credit_referral_on_signup
                    credit_referral_on_signup(
                        user=inactive_user,
                        referral_code=(ref_code or "").strip() or None,
                        source=(ref_source or "").strip() or None,
                        ip=request.META.get("REMOTE_ADDR"),
                        ua=request.META.get("HTTP_USER_AGENT"),
                    )
                except Exception:
                    pass

                return Response(
                    {"message": "Account restored. You can now sign in."},
                    status=status.HTTP_200_OK,
                )

        errors = {}
        if not username:
            errors["username"] = "This field is required."
        if not email:
            errors["email"] = "This field is required."
        if not password:
            errors["password"] = "This field is required."
        if User.objects.filter(username__iexact=username).exists():
            errors["username"] = "Username is already taken."
        if User.objects.filter(email__iexact=email).exists():
            errors["email"] = "Email is already registered."

        if not errors and password:
            try:
                validate_password(password)
            except ValidationError as exc:
                errors["password"] = list(exc.messages)

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = User.objects.create_user(username=username, email=email, password=password)
            # Activate designer accounts immediately
            user.is_active = True
            user.save()

            ensure_designer_access(user)
            ref_code = data.get("referral_code") or request.session.pop("referral_code", None)
            ref_source = data.get("referral_source") or request.session.pop("referral_source", None)
            try:
                from .services.referrals import credit_referral_on_signup
                credit_referral_on_signup(
                    user=user,
                    referral_code=(ref_code or "").strip() or None,
                    source=(ref_source or "").strip() or None,
                    ip=request.META.get("REMOTE_ADDR"),
                    ua=request.META.get("HTTP_USER_AGENT"),
                )
            except Exception:
                pass

            profile = user.designer_profile
            if website_url:
                try:
                    URLValidator()(website_url)
                    profile.portfolio_website = website_url
                    profile.save()
                except ValidationError:
                    pass

            plan_instance = None
            if subscription_plan:
                plan_instance = SubscriptionPlan.objects.filter(name=subscription_plan, is_active=True).first()

            trial_days = 30
            trial_end = timezone.now() + timedelta(days=trial_days)

            subscription = user.subscription
            update_fields = set()

            if plan_instance and subscription.plan != plan_instance:
                subscription.plan = plan_instance
                update_fields.add("plan")

            desired_payment_method = payment_method if payment_method else None
            if subscription.payment_method != desired_payment_method:
                subscription.payment_method = desired_payment_method
                update_fields.add("payment_method")

            for field_name in ["trial_end_date", "next_billing_date"]:
                if getattr(subscription, field_name) != trial_end:
                    setattr(subscription, field_name, trial_end)
                    update_fields.add(field_name)

            if subscription.trial_start_date is None:
                subscription.trial_start_date = timezone.now()
                update_fields.add("trial_start_date")

            if subscription.status != "free_trial":
                subscription.status = "free_trial"
                update_fields.add("status")

            if update_fields:
                subscription.save(update_fields=list(update_fields))

            transaction.on_commit(
                lambda: send_registration_notifications(user, request=request, source="api")
            )

        return Response(
            {"message": "Registration successful. You can now sign in."},
            status=status.HTTP_201_CREATED,
        )


class ReferralSummaryView(APIView):
    """GET /api/referrals/me/summary - Current user's referral stats and invite link."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from .services.referrals import ensure_referral_profile, next_tier_info

        ensure_referral_profile(request.user)
        profile = request.user.referral_profile
        base_url = getattr(settings, "BASE_URL_SERVER", "") or request.build_absolute_uri("/")[:-1]
        invite_url = f"{base_url}/invite/{profile.referral_code}/"

        tier_info = next_tier_info(profile)

        return Response({
            "referral_code": profile.referral_code,
            "invite_url": invite_url,
            "referral_count": profile.referral_count,
            "referral_points": profile.referral_points,
            "current_tier": (
                {"code": profile.current_tier.code, "name": profile.current_tier.name}
                if profile.current_tier else None
            ),
            "next_tier": tier_info.get("next"),
            "progress": tier_info.get("progress"),
        })


class ReferralLeaderboardView(APIView):
    """GET /api/referrals/leaderboard - Top referrers (public or authenticated)."""
    permission_classes = [AllowAny]

    def get(self, request):
        from .models import UserReferralProfile

        limit = min(int(request.GET.get("limit", 50)), 100)
        qs = (
            UserReferralProfile.objects.filter(referral_count__gt=0)
            .select_related("user", "current_tier")
            .order_by("-referral_count", "user__date_joined")[:limit]
        )
        rows = []
        for i, rp in enumerate(qs, 1):
            rows.append({
                "rank": i,
                "username": rp.user.username,
                "display_name": rp.user.get_full_name() or rp.user.username,
                "referral_count": rp.referral_count,
                "tier": {"code": rp.current_tier.code, "name": rp.current_tier.name} if rp.current_tier else None,
            })
        return Response({"leaderboard": rows})


@login_required
@require_POST
def webauthn_register_options(request):
    user = request.user

    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except (TypeError, ValueError):
        payload = {}

    nickname = (payload.get("nickname") or "").strip()

    exclude = [
        PublicKeyCredentialDescriptor(id=cred.credential_id)
        for cred in user.webauthn_credentials.all()
    ]

    selection = AuthenticatorSelectionCriteria(
        user_verification=UserVerificationRequirement.REQUIRED,
    )

    options = generate_registration_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        rp_name=settings.WEBAUTHN_RP_NAME,
        user=PublicKeyCredentialUserEntity(
            id=str(user.pk).encode("utf-8"),
            name=user.username,
            display_name=user.get_full_name() or user.username,
        ),
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=selection,
        exclude_credentials=exclude,
    )

    request.session["webauthn_registration_challenge"] = _base64url_from_bytes(options.challenge)
    request.session["webauthn_registration_nickname"] = nickname
    request.session.modified = True

    return JsonResponse(json.loads(options_to_json(options)))


@login_required
@require_POST
def webauthn_register_verify(request):
    expected_challenge = request.session.get("webauthn_registration_challenge")
    if not expected_challenge:
        return JsonResponse({"error": "missing_challenge"}, status=400)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid_payload"}, status=400)

    try:
        credential = RegistrationCredential.parse_raw(json.dumps(payload))
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"error": "invalid_credential", "detail": str(exc)}, status=400)

    try:
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGIN,
            require_user_verification=True,
            allow_insecure_localhost=settings.WEBAUTHN_ALLOW_INSECURE_LOCALHOST,
        )
    except Exception as exc:  # noqa: BLE001
        request.session.pop("webauthn_registration_challenge", None)
        request.session.pop("webauthn_registration_nickname", None)
        request.session.modified = True
        return JsonResponse({"error": "registration_failed", "detail": str(exc)}, status=400)

    transports = getattr(credential.response, "transports", None) or []
    nickname = request.session.pop("webauthn_registration_nickname", "").strip()

    credential_obj, _ = WebAuthnCredential.objects.update_or_create(
        user=request.user,
        credential_id=verification.credential_id,
        defaults={
            "public_key": verification.credential_public_key,
            "sign_count": verification.sign_count,
            "transports": transports,
            "nickname": nickname,
        },
    )

    request.session.pop("webauthn_registration_challenge", None)
    request.session.modified = True

    return JsonResponse(
        {
            "status": "ok",
            "credential_id": _base64url_from_bytes(verification.credential_id),
            "credential_pk": credential_obj.pk,
        }
    )


@require_POST
def webauthn_authenticate_options(request):
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except (TypeError, ValueError):
        payload = {}

    identifier = payload.get("username") or payload.get("email")
    user = _find_user_by_identifier(identifier)

    if not user or not user.is_active:
        return JsonResponse({"error": "user_not_found"}, status=404)

    credentials = list(WebAuthnCredential.objects.filter(user=user))
    if not credentials:
        return JsonResponse({"error": "no_passkeys"}, status=400)

    options = generate_authentication_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=cred.credential_id)
            for cred in credentials
        ],
        user_verification=UserVerificationRequirement.REQUIRED,
    )

    request.session["webauthn_authentication_challenge"] = _base64url_from_bytes(options.challenge)
    request.session["webauthn_authentication_user_id"] = user.pk
    request.session.modified = True

    return JsonResponse(json.loads(options_to_json(options)))


@require_POST
def webauthn_authenticate_verify(request):
    expected_challenge = request.session.get("webauthn_authentication_challenge")
    user_id = request.session.get("webauthn_authentication_user_id")

    if not expected_challenge or not user_id:
        return JsonResponse({"error": "missing_challenge"}, status=400)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid_payload"}, status=400)

    remember_me = bool(payload.get("remember_me"))
    next_url = payload.get("next") or ""

    try:
        credential = AuthenticationCredential.parse_raw(json.dumps(payload))
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"error": "invalid_credential", "detail": str(exc)}, status=400)

    UserModel = get_user_model()
    try:
        user = UserModel.objects.get(pk=user_id, is_active=True)
    except UserModel.DoesNotExist:
        request.session.pop("webauthn_authentication_challenge", None)
        request.session.pop("webauthn_authentication_user_id", None)
        request.session.modified = True
        return JsonResponse({"error": "user_not_found"}, status=404)

    raw_id = payload.get("rawId")
    if not raw_id:
        return JsonResponse({"error": "missing_credential_id"}, status=400)

    credential_id = _bytes_from_base64url(raw_id)

    try:
        stored_credential = WebAuthnCredential.objects.get(user=user, credential_id=credential_id)
    except WebAuthnCredential.DoesNotExist:
        return JsonResponse({"error": "credential_not_found"}, status=404)

    try:
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGIN,
            credential_public_key=stored_credential.public_key,
            credential_current_sign_count=stored_credential.sign_count,
            require_user_verification=True,
            allow_insecure_localhost=settings.WEBAUTHN_ALLOW_INSECURE_LOCALHOST,
        )
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"error": "authentication_failed", "detail": str(exc)}, status=400)

    stored_credential.sign_count = verification.new_sign_count
    stored_credential.last_used_at = timezone.now()
    stored_credential.save(update_fields=["sign_count", "last_used_at", "updated_at"])

    request.session.pop("webauthn_authentication_challenge", None)
    request.session.pop("webauthn_authentication_user_id", None)
    request.session.modified = True

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    if remember_me:
        session_age_seconds = getattr(settings, "REMEMBER_ME_SESSION_AGE", 60 * 60 * 24 * 30)
        request.session.set_expiry(session_age_seconds)
    else:
        request.session.set_expiry(0)

    redirect_to = _resolve_post_login_redirect(request, next_url)
    return JsonResponse({"status": "ok", "redirect_url": redirect_to})


@login_required
@require_POST
def webauthn_delete_credential(request, credential_id):
    try:
        credential = request.user.webauthn_credentials.get(pk=credential_id)
    except WebAuthnCredential.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)

    credential.delete()
    return JsonResponse({"status": "ok"})
# Placeholder functions
def upload_design(request):
    if request.user.is_authenticated:
        return redirect("designer_design_create")
    return redirect("login")


def approve_designer(request, user_id):
    return JsonResponse({"status": "ok"})


def reject_designer(request, user_id):
    return JsonResponse({"status": "ok"})


def reinstate_designer(request, designer_id):
    return JsonResponse({"status": "ok"})


@login_required
def designer_design_edit_view(request, design_id):
    design = get_object_or_404(Design, pk=design_id, designer=request.user)

    if request.method == "POST":
        updated_design, errors = _save_design_from_request(request, design=design)
        if errors:
            if _request_wants_json(request):
                return JsonResponse({"success": False, "errors": errors}, status=400)

            messages.error(request, "Please correct the highlighted errors.")
            context = {
                "current_section": "designs",
                "design": updated_design,
                "form_errors": errors,
                "gallery_images": updated_design.images.order_by("order", "created_at"),
            }
            return render(
                request,
                "designer_portfolio/designer_design_edit.html",
                context,
                status=400,
            )

        state_message = "Design updated and published." if updated_design.published else "Design updated as draft."
        messages.success(request, state_message)
        if _request_wants_json(request):
            return JsonResponse(
                {
                    "success": True,
                    "design_id": updated_design.pk,
                    "redirect_url": reverse("designer_designs"),
                }
            )
        return redirect("designer_designs")

    context = {
        "current_section": "designs",
        "design": design,
        "form_errors": {},
        "gallery_images": design.images.order_by("order", "created_at"),
    }
    return render(request, "designer_portfolio/designer_design_edit.html", context)


@login_required
@require_POST
def designer_design_delete_view(request, design_id):
    design = get_object_or_404(Design, pk=design_id, designer=request.user)
    design.delete()

    messages.success(request, "Design deleted successfully.")
    if _request_wants_json(request):
        return JsonResponse(
            {
                "success": True,
                "redirect_url": reverse("designer_designs"),
            }
        )
    return redirect("designer_designs")


@login_required
def designer_design_detail_api(request, design_id):
    design = get_object_or_404(Design, pk=design_id, designer=request.user)

    data = {
        "id": design.pk,
        "title": design.title,
        "slug": design.slug,
        "season": design.season,
        "year": design.year,
        "description": design.description,
        "published": design.published,
        "category": design.category,
        "target_market": design.target_market,
        "featured": design.featured,
        "fabric_type": design.fabric_type,
        "fabric_weight": design.fabric_weight,
        "fabric_details": design.fabric_details,
        "color_palette": design.color_palette,
        "size_range": design.size_range,
        "target_price": str(design.target_price) if design.target_price is not None else "",
        "production_notes": design.production_notes,
        "design_notes": design.design_notes,
        "has_techpack": design.has_techpack,
        "techpack_pdf": design.techpack_pdf.url if design.techpack_pdf else "",
        "techpack_excel": design.techpack_excel.url if design.techpack_excel else "",
        "cover_image": design.cover_image.url if design.cover_image else "",
        "created_at": design.created_at.isoformat() if design.created_at else "",
        "updated_at": design.updated_at.isoformat() if design.updated_at else "",
        "detail_url": reverse("design_detail", args=[design.slug]) if design.slug else "",
    }
    data["images"] = [
        {
            "id": image.pk,
            "url": image.image.url,
            "order": image.order,
            "caption": image.caption,
        }
        for image in design.images.order_by("order", "created_at")
    ]

    return JsonResponse({"success": True, "design": data})


def membership_upgrade(request):
    """Public designer membership upgrade guide and plan comparison."""
    from .membership_plans import (
        ACTIVATION_CHECKLIST,
        PAYMENT_METHODS,
        UPGRADE_STEPS,
        list_membership_plans,
    )
    from . import stripe_billing

    plans_url = reverse("subscription_dashboard")
    if request.user.is_authenticated:
        select_plan_url = plans_url
    else:
        select_plan_url = f"{reverse('login')}?next={plans_url}"

    return render(
        request,
        "designer_portfolio/membership_upgrade.html",
        {
            "membership_plans": list_membership_plans(),
            "payment_methods_list": PAYMENT_METHODS,
            "activation_checklist": ACTIVATION_CHECKLIST,
            "upgrade_steps": UPGRADE_STEPS,
            "register_url": reverse("signup"),
            "login_url": reverse("login"),
            "select_plan_url": select_plan_url,
            "plans_dashboard_url": plans_url,
            "is_authenticated": request.user.is_authenticated,
            "stripe_enabled": stripe_billing.is_configured(),
        },
    )


@login_required
def subscription_dashboard(request):
    from .auth_utils import ensure_designer_access
    from .membership_plans import (
        ACTIVATION_CHECKLIST,
        PAYMENT_METHODS,
        UPGRADE_STEPS,
        list_membership_plans,
    )
    from . import stripe_billing

    ensure_designer_access(request.user)
    subscription = (
        UserSubscription.objects.select_related("plan").filter(user=request.user).first()
    )
    checkout_success = request.GET.get("checkout") == "success"
    is_active = subscription and subscription.status == "active"
    billing_portal_available = (
        bool(subscription and subscription.stripe_customer_id)
        and stripe_billing.is_configured()
    )
    return render(
        request,
        "designer_portfolio/subscription_dashboard.html",
        {
            "current_section": "subscription",
            "subscription": subscription,
            "membership_plans": list_membership_plans(),
            "payment_methods_list": PAYMENT_METHODS,
            "activation_checklist": ACTIVATION_CHECKLIST,
            "upgrade_steps": UPGRADE_STEPS,
            "stripe_enabled": stripe_billing.is_configured(),
            "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
            "checkout_success": checkout_success,
            "show_activation": checkout_success or is_active,
            "billing_portal_available": billing_portal_available,
            "register_url": reverse("signup"),
            "login_url": reverse("login"),
        },
    )


@login_required
@require_POST
def change_subscription_plan(request):
    from . import stripe_billing

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid request."}, status=400)

    plan_slug = (payload.get("plan") or payload.get("plan_slug") or "").strip()
    interval = (payload.get("interval") or "monthly").strip().lower()
    if interval not in {"monthly", "yearly"}:
        return JsonResponse({"error": "Invalid billing interval."}, status=400)
    if not plan_slug:
        return JsonResponse({"error": "Choose a membership plan."}, status=400)

    if not stripe_billing.is_configured():
        return JsonResponse(
            {"error": "Online payments are not configured yet. Contact support."},
            status=503,
        )

    try:
        session = stripe_billing.create_membership_checkout_session(
            user=request.user,
            plan_slug=plan_slug,
            interval=interval,
            success_url=request.build_absolute_uri(reverse("subscription_dashboard")),
            cancel_url=request.build_absolute_uri(reverse("subscription_dashboard")),
        )
    except stripe_billing.StripeBillingError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse({"checkout_url": session.url})


@login_required
@require_POST
def cancel_subscription(request):
    from . import stripe_billing

    subscription = UserSubscription.objects.filter(user=request.user).first()
    if subscription is None:
        return JsonResponse({"error": "No subscription found."}, status=404)

    if subscription.stripe_subscription_id and stripe_billing.is_configured():
        try:
            stripe_billing.cancel_stripe_subscription(subscription)
        except stripe_billing.StripeBillingError as exc:
            return JsonResponse({"error": str(exc)}, status=400)

    subscription.auto_renewal = False
    if subscription.status == "active":
        subscription.status = "canceled"
    subscription.save(update_fields=["auto_renewal", "status", "updated_at"])
    return JsonResponse({"status": "canceled"})


@login_required
@require_POST
def create_stripe_billing_portal_session(request):
    from . import stripe_billing

    if not stripe_billing.is_configured():
        return JsonResponse(
            {"error": "Stripe is not configured."},
            status=503,
        )

    try:
        session = stripe_billing.create_billing_portal_session(
            user=request.user,
            return_url=request.build_absolute_uri(reverse("subscription_dashboard")),
        )
    except stripe_billing.StripeBillingError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse({"portal_url": session.url})


@login_required
def payment_methods(request):
    from .auth_utils import ensure_designer_access
    from . import stripe_billing

    ensure_designer_access(request.user)
    subscription = (
        UserSubscription.objects.select_related("plan").filter(user=request.user).first()
    )
    saved_card = None
    if subscription and subscription.stripe_customer_id and stripe_billing.is_configured():
        try:
            saved_card = stripe_billing.get_default_payment_method_summary(
                subscription.stripe_customer_id
            )
        except Exception:
            saved_card = None

    return render(
        request,
        "designer_portfolio/payment_methods.html",
        {
            "current_section": "subscription",
            "subscription": subscription,
            "saved_card": saved_card,
            "stripe_enabled": stripe_billing.is_configured(),
            "stripe_publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
        },
    )

@login_required
def billing_history(request):
    from .auth_utils import ensure_designer_access
    from . import stripe_billing

    ensure_designer_access(request.user)
    subscription = (
        UserSubscription.objects.select_related("plan").filter(user=request.user).first()
    )
    invoices = []
    billing_history_error = ""
    if subscription and subscription.stripe_customer_id and stripe_billing.is_configured():
        try:
            invoices = stripe_billing.list_customer_invoices(subscription)
        except stripe_billing.StripeBillingError as exc:
            billing_history_error = str(exc)

    if not invoices and subscription:
        local_invoice = stripe_billing.local_invoice_entry(subscription)
        if local_invoice:
            invoices = [local_invoice]

    return render(
        request,
        "designer_portfolio/billing_history.html",
        {
            "current_section": "subscription",
            "subscription": subscription,
            "invoices": invoices,
            "billing_history_error": billing_history_error,
        },
    )

@login_required
@require_POST
def create_stripe_setup_intent(request):
    from . import stripe_billing

    if not stripe_billing.is_configured():
        return JsonResponse(
            {"error": "Stripe is not configured."},
            status=503,
        )
    try:
        intent = stripe_billing.create_setup_intent(request.user)
    except stripe_billing.StripeBillingError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({"client_secret": intent.client_secret})


@csrf_exempt
@require_POST
def stripe_webhook(request):
    from . import stripe_billing

    signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        stripe_billing.handle_webhook_event(request.body, signature)
    except stripe_billing.StripeBillingError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except ValueError:
        return JsonResponse({"error": "Invalid payload."}, status=400)
    return JsonResponse({"status": "ok"})

def create_paypal_subscription(request):
    return JsonResponse({"status": "ok"})

def paypal_webhook(request):
    return JsonResponse({"status": "ok"})

def generate_techpack(request, slug):
    blueprint = get_techpack_blueprint(slug)
    if not blueprint:
        raise Http404("Requested techpack blueprint was not found.")

    hero = blueprint.get("hero", {})
    project_breakdown = blueprint.get("project_breakdown", {})
    hero_title = hero.get("title") or blueprint.get("title") or "Techpack"
    breakdown_label = project_breakdown.get("label")
    page_title = f"{hero_title} — {breakdown_label}" if breakdown_label else hero_title

    return render(
        request,
        "designer_portfolio/techpack_blueprint.html",
        {
            "blueprint": blueprint,
            "page_title": page_title,
        },
    )

@login_required
def dashboard_view(request):
    return render(request, "designer_portfolio/dashboard.html", {"current_section": "dashboard"})

@login_required
def designer_designs_view(request):
    # Ensure related records exist
    DesignerProfile.objects.get_or_create(user=request.user)
    if not hasattr(request.user, "subscription"):
        trial_end = timezone.now() + timedelta(days=30)
        UserSubscription.objects.create(
            user=request.user,
            plan=None,
            status="free_trial",
            payment_method=None,
            trial_end_date=trial_end,
            next_billing_date=trial_end,
        )

    designs = Design.objects.filter(designer=request.user).order_by("-created_at")
    available_years = (
        designs.values_list("year", flat=True).distinct().order_by("-year")
    )

    return render(
        request,
        "designer_portfolio/designer_designs.html",
        {
            "current_section": "designs",
            "designs": designs,
            "available_years": available_years,
        },
    )

@login_required
def designer_design_create_view(request):
    # Ensure related records exist
    DesignerProfile.objects.get_or_create(user=request.user)
    if not hasattr(request.user, "subscription"):
        trial_end = timezone.now() + timedelta(days=30)
        UserSubscription.objects.create(
            user=request.user,
            plan=None,
            status="free_trial",
            payment_method=None,
            trial_end_date=trial_end,
            next_billing_date=trial_end,
        )

    context = {
        "current_section": "designs",
        "current_year": timezone.now().year,
        "form_errors": {},
        "form_values": {},
    }

    if request.method == "POST":
        design, errors = _save_design_from_request(request)
        if errors:
            if _request_wants_json(request):
                return JsonResponse({"success": False, "errors": errors}, status=400)

            messages.error(request, "Please correct the highlighted errors.")
            context["form_errors"] = errors
            context["form_values"] = {key: value for key, value in request.POST.items()}
            return render(
                request,
                "designer_portfolio/designer_design_create.html",
                context,
                status=400,
            )

        success_message = (
            "Design uploaded and published." if design.published else "Design saved as draft."
        )
        messages.success(request, success_message)

        if _request_wants_json(request):
            return JsonResponse(
                {
                    "success": True,
                    "design_id": design.pk,
                    "redirect_url": reverse("designer_designs"),
                }
            )

        return redirect("designer_designs")

    return render(request, "designer_portfolio/designer_design_create.html", context)

@login_required
def designer_about_me_view(request):
    user = request.user
    profile, _ = DesignerProfile.objects.get_or_create(user=user)

    # Ensure a subscription record exists (for templates using it)
    if not hasattr(user, "subscription"):
        trial_end = timezone.now() + timedelta(days=30)
        UserSubscription.objects.create(
            user=user,
            plan=None,
            status="free_trial",
            payment_method=None,
            trial_end_date=trial_end,
            next_billing_date=trial_end,
        )

    passkeys = list(user.webauthn_credentials.order_by("created_at"))

    if request.method == "POST":
        def cleaned_post(key, current_value):
            if key not in request.POST:
                return current_value
            return (request.POST.get(key) or "").strip()

        # Update basic user fields
        first_name = (request.POST.get("first_name") or user.first_name).strip()
        last_name = (request.POST.get("last_name") or user.last_name).strip()
        email = (request.POST.get("email") or user.email).strip()

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()

        # Update profile fields (map template inputs to model fields)
        profile.bio = cleaned_post("bio", profile.bio)
        profile.location = cleaned_post("location", profile.location)
        profile.education = cleaned_post("education", profile.education)
        profile.region_area = cleaned_post("region_area", profile.region_area)
        profile.country = cleaned_post("country", profile.country)
        profile.state_province = cleaned_post("state_province", profile.state_province)
        profile.county = cleaned_post("county", profile.county)
        profile.city = cleaned_post("city", profile.city)
        # years_of_experience may be empty; coerce safely
        years_val = request.POST.get("years_of_experience", "").strip()
        try:
            profile.years_of_experience = int(years_val) if years_val != "" else profile.years_of_experience
        except ValueError:
            # leave unchanged on bad input
            pass

        # Social/portfolio links
        if "portfolio_website" in request.POST:
            profile.portfolio_website = (request.POST.get("portfolio_website") or "").strip()
        elif "website" in request.POST:
            profile.portfolio_website = (request.POST.get("website") or "").strip()

        if "instagram_handle" in request.POST:
            profile.instagram_handle = (request.POST.get("instagram_handle") or "").strip()
        elif "instagram" in request.POST:
            profile.instagram_handle = (request.POST.get("instagram") or "").strip()

        if "linkedin_profile" in request.POST:
            profile.linkedin_profile = (request.POST.get("linkedin_profile") or "").strip()
        elif "linkedin" in request.POST:
            profile.linkedin_profile = (request.POST.get("linkedin") or "").strip()

        if "specialization" in request.POST:
            profile.specialization = (request.POST.get("specialization") or "").strip()
        elif "specializations" in request.POST:
            profile.specialization = (request.POST.get("specializations") or "").strip()

        profile.contact_email = cleaned_post("contact_email", profile.contact_email)

        # Collaboration preference (support old and corrected field names)
        available_flag = request.POST.get("available_for_collaborations") or request.POST.get("available_for_collaboration")
        profile.available_for_collaborations = bool(available_flag)

        # Handle profile image upload
        if "profile_image" in request.FILES:
            profile.profile_image = request.FILES["profile_image"]

        profile.save()

        messages.success(request, "Your profile was updated successfully.")
        return redirect("designer_about_me")

    # Stats for header widgets
    try:
        total_designs = Design.objects.filter(designer=user).count()
    except Exception:
        total_designs = 0

    return render(
        request,
        "designer_portfolio/designer_about_me.html",
        {
            "current_section": "about",
            "designer_profile": profile,
            "total_designs": total_designs,
            "passkeys": passkeys,
        },
    )


@login_required
def designer_change_password_view(request):
    """Handle password change requests via AJAX"""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)
    
    try:
        import json
        data = json.loads(request.body)
        current_password = data.get("current_password", "")
        new_password1 = data.get("new_password1", "")
        new_password2 = data.get("new_password2", "")
        
        # Validate inputs
        if not current_password or not new_password1 or not new_password2:
            return JsonResponse({"error": "All password fields are required"}, status=400)
        
        if new_password1 != new_password2:
            return JsonResponse({"error": "New passwords do not match"}, status=400)
        
        # Check current password
        user = request.user
        if not user.check_password(current_password):
            return JsonResponse({"error": "Current password is incorrect"}, status=400)
        
        # Validate new password
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        
        try:
            validate_password(new_password1, user)
        except ValidationError as e:
            return JsonResponse({"error": "; ".join(e.messages)}, status=400)
        
        # Change password
        user.set_password(new_password1)
        user.save()
        
        # Update session to keep user logged in
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, user)
        
        return JsonResponse({"success": True, "message": "Password changed successfully"})
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse({"error": "An error occurred while changing password"}, status=500)

@login_required
def designer_contact_view(request):
    profile, _ = DesignerProfile.objects.get_or_create(user=request.user)
    if not hasattr(request.user, "subscription"):
        trial_end = timezone.now() + timedelta(days=30)
        UserSubscription.objects.create(
            user=request.user,
            plan=None,
            status="free_trial",
            payment_method=None,
            trial_end_date=trial_end,
            next_billing_date=trial_end,
        )

    # Count non-empty social links for small stat
    social_links_count = sum(
        1
        for value in [
            getattr(profile, "portfolio_website", ""),
            getattr(profile, "instagram_handle", ""),
            getattr(profile, "linkedin_profile", ""),
        ]
        if value
    )

    return render(
        request,
        "designer_portfolio/designer_contact.html",
        {
            "current_section": "contact",
            "designer_profile": profile,
            "social_links_count": social_links_count,
        },
    )

from django.contrib.auth import logout
def logout_view(request):
    logout(request)
    return redirect('home')

def unified_search_view(request):
    """Search exclusively for filtering designers, collections, and events (e.g. fashion shows, popup events). GET: q (optional), type (designers|collections|events|all)."""
    q = (request.GET.get("q") or "").strip()
    type_filter = (request.GET.get("type") or "all").lower()
    if type_filter not in ("all", "designers", "collections", "events"):
        type_filter = "all"

    designers = []
    collections = []
    events = []
    total_count = 0
    search_term = q

    # Filter by type first; with or without keyword search
    if type_filter in ("all", "designers"):
        qs = DesignerProfile.objects.filter(user__is_active=True).select_related("user")
        if search_term:
            qs = qs.filter(
                Q(user__username__icontains=search_term)
                | Q(user__first_name__icontains=search_term)
                | Q(user__last_name__icontains=search_term)
                | Q(bio__icontains=search_term)
                | Q(specialization__icontains=search_term)
                | Q(location__icontains=search_term)
                | Q(region_area__icontains=search_term)
                | Q(country__icontains=search_term)
                | Q(state_province__icontains=search_term)
                | Q(county__icontains=search_term)
                | Q(city__icontains=search_term)
            )
        designers = list(qs[:50])
    if type_filter in ("all", "collections"):
        qs = Collection.objects.filter(published=True)
        if search_term:
            qs = qs.filter(
                Q(name__icontains=search_term)
                | Q(description__icontains=search_term)
                | Q(season__icontains=search_term)
                | Q(designer__icontains=search_term)
            )
        collections = list(qs[:50])
    if type_filter in ("all", "events"):
        qs = Event.objects.all()
        if search_term:
            qs = qs.filter(
                Q(title__icontains=search_term)
                | Q(description__icontains=search_term)
                | Q(location__icontains=search_term)
                | Q(venue__icontains=search_term)
            )
        events = list(qs[:50])
    total_count = len(designers) + len(collections) + len(events)

    return render(
        request,
        "designer_portfolio/search_results.html",
        {
            "query": q,
            "type_filter": type_filter,
            "designers": designers,
            "collections": collections,
            "events": events,
            "total_count": total_count,
        },
    )


def designer_public_detail_view(request, user_id):
    """Public designer profile; shows Continue and Ask a question (auth modal for anonymous)."""
    user_obj = get_object_or_404(User, pk=user_id, is_active=True)
    try:
        profile = DesignerProfile.objects.select_related("user").get(user=user_obj)
    except DesignerProfile.DoesNotExist:
        raise Http404("Designer profile not found")
    return render(
        request,
        "designer_portfolio/designer_public_detail.html",
        {"designer": profile, "profile_user": user_obj},
    )


class DesignersListView(ListView):
    model = DesignerProfile
    template_name = "designer_portfolio/designers.html"
    context_object_name = "designers"
    paginate_by = 20
    LOCATION_FIELDS = [
        ("area", "Area / Region"),
        ("country", "Country"),
        ("state", "State / Province"),
        ("county", "County"),
        ("city", "City"),
    ]
    LOCATION_PARAM_ORDER = [name for name, _ in LOCATION_FIELDS]
    LOCATION_PARAM_FIELD_MAP = {
        "area": "region_area",
        "country": "country",
        "state": "state_province",
        "county": "county",
        "city": "city",
    }

    def _base_queryset(self):
        return (
            DesignerProfile.objects.filter(user__is_active=True)
            .select_related("user")
        )

    def get_queryset(self):
        qs = self._base_queryset()
        filters = self._selected_location_filters()

        if filters["area"]:
            qs = qs.filter(region_area__iexact=filters["area"])
        if filters["country"]:
            qs = qs.filter(country__iexact=filters["country"])
        if filters["state"]:
            qs = qs.filter(state_province__iexact=filters["state"])
        if filters["county"]:
            qs = qs.filter(county__iexact=filters["county"])
        if filters["city"]:
            qs = qs.filter(city__iexact=filters["city"])

        qs = qs.order_by("-created_at")
        self._filtered_queryset = qs
        self._result_count = qs.count()
        return qs

    def _normalize_value(self, value: str) -> str:
        return (value or "").strip()

    def _selected_location_filters(self) -> dict[str, str]:
        if not hasattr(self, "_location_filter_cache"):
            self._location_filter_cache = {
                param: self._normalize_value(self.request.GET.get(param))
                for param in self.LOCATION_PARAM_ORDER
            }
        return self._location_filter_cache

    def _location_rows(self):
        if not hasattr(self, "_location_rows_cache"):
            fields = list(self.LOCATION_PARAM_FIELD_MAP.values())
            self._location_rows_cache = list(
                DesignerProfile.objects.filter(user__is_active=True).values(*fields)
            )
        return self._location_rows_cache

    def _row_matches(self, row: dict, depend_params: list[str]) -> bool:
        filters = self._selected_location_filters()
        for param in depend_params:
            selected_value = filters.get(param)
            if not selected_value:
                continue
            field_name = self.LOCATION_PARAM_FIELD_MAP[param]
            row_value = self._normalize_value(row.get(field_name))
            if not row_value:
                return False
            if row_value.casefold() != selected_value.casefold():
                return False
        return True

    def _option_list(self, target_param: str, depend_params: list[str]) -> list[dict]:
        field_name = self.LOCATION_PARAM_FIELD_MAP[target_param]
        counters: dict[str, dict] = {}
        for row in self._location_rows():
            if not self._row_matches(row, depend_params):
                continue
            value = self._normalize_value(row.get(field_name))
            if not value:
                continue
            key = value.casefold()
            entry = counters.setdefault(
                key,
                {
                    "value": value,
                    "label": value,
                    "count": 0,
                },
            )
            entry["count"] += 1

        return sorted(counters.values(), key=lambda item: item["label"].lower())

    def _downstream_params(self, param: str) -> list[str]:
        if param not in self.LOCATION_PARAM_ORDER:
            return []
        start_index = self.LOCATION_PARAM_ORDER.index(param) + 1
        return self.LOCATION_PARAM_ORDER[start_index:]

    def _build_remove_filter_url(self, param: str) -> str:
        params_to_clear = [param] + self._downstream_params(param)
        query: QueryDict = self.request.GET.copy()
        for key in params_to_clear:
            if key in query:
                query.pop(key, None)
        query.pop("page", None)
        encoded = query.urlencode()
        return f"{self.request.path}?{encoded}" if encoded else self.request.path

    def _build_clear_filters_url(self) -> str:
        query: QueryDict = self.request.GET.copy()
        for key in self.LOCATION_PARAM_FIELD_MAP.keys():
            query.pop(key, None)
        query.pop("page", None)
        encoded = query.urlencode()
        return f"{self.request.path}?{encoded}" if encoded else self.request.path

    def _build_active_filter_chips(self) -> list[dict]:
        chips = []
        labels = dict(self.LOCATION_FIELDS)
        filters = self._selected_location_filters()
        for param in self.LOCATION_PARAM_ORDER:
            value = filters.get(param)
            if not value:
                continue
            chips.append(
                {
                    "param": param,
                    "label": labels[param],
                    "value": value,
                    "remove_url": self._build_remove_filter_url(param),
                }
            )
        return chips

    def _build_location_filter_context(self) -> dict:
        filters = self._selected_location_filters()
        options = {
            "area": self._option_list("area", []),
            "country": self._option_list("country", ["area"]),
            "state": self._option_list("state", ["area", "country"]),
            "county": self._option_list("county", ["area", "country", "state"]),
            "city": self._option_list("city", ["area", "country", "state", "county"]),
        }

        fields_payload = []
        for name, label in self.LOCATION_FIELDS:
            fields_payload.append(
                {
                    "name": name,
                    "label": label,
                    "options": options[name],
                    "selected": filters.get(name, ""),
                }
            )

        chips = self._build_active_filter_chips()
        return {
            "fields": fields_payload,
            "selected": filters,
            "active_chips": chips,
            "has_active": bool(chips),
            "clear_url": self._build_clear_filters_url(),
            "order": ",".join(self.LOCATION_PARAM_ORDER),
            "result_count": getattr(self, "_result_count", 0),
        }

    def _get_result_count(self) -> int:
        return getattr(self, "_result_count", 0)

    def get_context_data(self, **kwargs):
        """Expose viewer metadata for the follow interactions on the page."""
        context = super().get_context_data(**kwargs)
        user = self.request.user
        viewer_name = ""
        if getattr(user, "is_authenticated", False):
            viewer_name = (user.get_full_name() or "").strip() or user.username

        context["designer_result_count"] = self._get_result_count()
        context["location_filters"] = self._build_location_filter_context()
        context.update(
            {
                "viewer_name": viewer_name,
                "viewer_is_authenticated": bool(getattr(user, "is_authenticated", False)),
            }
        )
        return context


def health_check(request):
    """Minimal health check for load balancers and 502 debugging. No DB, no template."""
    # Debug: show Google OAuth redirect URI when ?google_redirect=1 (DEBUG or GOOGLE_OAUTH_DEBUG=1)
    oauth_debug = os.getenv("GOOGLE_OAUTH_DEBUG", "").strip().lower() in ("1", "true", "yes")
    if (getattr(settings, "DEBUG", False) or oauth_debug) and request.GET.get("google_redirect"):
        base = request.build_absolute_uri("/").rstrip("/")
        redirect_uri = f"{base}/auth/complete/google-oauth2/"
        return JsonResponse(
            {
                "message": "Add this exact URI to Google Cloud Console → Credentials → Authorized redirect URIs",
                "redirect_uri": redirect_uri,
                "host": request.get_host(),
                "scheme": request.scheme,
            }
        )
    return HttpResponse("ok", content_type="text/plain", status=200)


def designer_ai_config_check(request):
    """
    Verify Designer AI / OpenAI config is loaded. Does NOT expose the API key.
    Use this to confirm OPENAI_API_KEY is available to the running process.
    """
    key = os.getenv("OPENAI_API_KEY")
    configured = bool(key and key.strip())
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    try:
        has_openai = __import__("openai")
    except ImportError:
        has_openai = None

    return JsonResponse({
        "openai_configured": configured,
        "openai_library_installed": has_openai is not None,
        "model": model,
        "status": "ok" if (configured and has_openai) else "degraded",
        "message": (
            "Designer AI is ready (OpenAI + key loaded)."
            if configured and has_openai
            else "Designer AI will use fallback responses. Set OPENAI_API_KEY and run: pip install openai"
        ),
    })


def _resolve_post_login_redirect(request, candidate: str | None = "") -> str:
    """Return a safe redirect target after authentication flows."""

    fallback = resolve_url(getattr(settings, "LOGIN_REDIRECT_URL", "designer_dashboard"))
    if not candidate:
        return fallback

    allowed_hosts = {request.get_host()}
    for host in getattr(settings, "ALLOWED_HOSTS", []) or []:
        cleaned = (host or "").strip()
        if cleaned and cleaned != "*":
            allowed_hosts.add(cleaned)

    if url_has_allowed_host_and_scheme(candidate, allowed_hosts=allowed_hosts, require_https=request.is_secure()):
        return candidate
    return fallback


class DesignerLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = DesignerLoginForm

    def _provider_enabled(self, key_attr: str, secret_attr: str) -> bool:
        key = getattr(settings, key_attr, "") or ""
        secret = getattr(settings, secret_attr, "") or ""
        return bool(key and secret)

    def _google_enabled(self) -> bool:
        return _google_oauth_ready()

    def post(self, request, *args, **kwargs):
        """Reject password login when Gmail is mandatory."""
        if getattr(settings, "GOOGLE_LOGIN_MANDATORY", False):
            messages.info(
                request,
                "Please sign in with your Gmail account to access your dashboard.",
            )
            return self.get(request, *args, **kwargs)
        return super().post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["google_login_mandatory"] = getattr(
            settings, "GOOGLE_LOGIN_MANDATORY", False
        )
        context["google_login_available"] = self._google_enabled()
        provider_catalog = [
            (
                "SOCIAL_AUTH_GOOGLE_OAUTH2_KEY",
                "SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET",
                "google-oauth2",
                "Google",
                "google",
                "G",
            ),
            (
                "SOCIAL_AUTH_LINKEDIN_OAUTH2_KEY",
                "SOCIAL_AUTH_LINKEDIN_OAUTH2_SECRET",
                "linkedin-oauth2",
                "LinkedIn",
                "linkedin",
                "in",
            ),
            (
                "SOCIAL_AUTH_INSTAGRAM_KEY",
                "SOCIAL_AUTH_INSTAGRAM_SECRET",
                "instagram",
                "Instagram",
                "instagram",
                "IG",
            ),
        ]

        providers = []
        for key_attr, secret_attr, backend_name, label, css_class, icon in provider_catalog:
            if (backend_name == "google-oauth2" and _google_oauth_ready()) or self._provider_enabled(key_attr, secret_attr):
                providers.append(
                    {
                        "backend": backend_name,
                        "label": label,
                        "css_class": css_class,
                        "icon": icon,
                    }
                )

        context["social_login_providers"] = providers
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        remember_me = form.cleaned_data.get("remember_me")

        # Control session expiry based on remember_me
        # When remember_me is True, use a longer session age; otherwise expire at browser close
        if remember_me:
            # Use custom setting if provided; fallback to 30 days
            session_age_seconds = getattr(settings, "REMEMBER_ME_SESSION_AGE", 60 * 60 * 24 * 30)
            self.request.session.set_expiry(session_age_seconds)
        else:
            # 0 = expire at browser close
            self.request.session.set_expiry(0)

        return response


class DesignerPasswordResetView(PasswordResetView):
    form_class = DesignerPasswordResetForm
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")


class DesignerPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "registration/password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")

    def form_valid(self, form):
        response = super().form_valid(form)
        user = getattr(self, "user", None)
        if user is not None:
            notify_user_password_reset_completion(user, request=self.request)
        return response


# --- Security/Errors ---
@requires_csrf_token
def csrf_failure(request, reason=""):
    """Custom handler for CSRF failures.

    Returns JSON for AJAX/JSON requests and a friendly HTML page otherwise.
    """
    accepts_header = (request.headers.get("Accept") or "").lower()
    is_ajax = (request.headers.get("x-requested-with") or "").lower() == "xmlhttprequest"
    wants_json = "application/json" in accepts_header

    if is_ajax or wants_json:
        payload = {
            "error": "csrf_failed",
            "message": "Your session expired or the form is stale. Please refresh the page and try again.",
        }
        if settings.DEBUG:
            payload["reason"] = reason or ""
        return JsonResponse(payload, status=403)

    context = {
        "reason": reason or "",
        "debug": settings.DEBUG,
    }
    return render(request, "errors/403_csrf.html", context=context, status=403)


# ==================== Designer AI Chat ====================

def _get_designer_ai_system_prompt() -> str:
    """Returns the system prompt for Designer AI."""
    from .ai.chat_assistant import get_system_prompt

    return get_system_prompt()


def _build_infrastructure_response() -> str:
    """Generate a reusable explanation of GDH infrastructure details."""
    canonical_host = getattr(settings, "CANONICAL_HOST", "globaldesignerhub.com")
    reference_doc_path = getattr(settings, "INFRASTRUCTURE_DOC_PATH", "/docs/platform/reference-architecture")
    return f"""Here's how {canonical_host} keeps performance high and resilient worldwide:

**Platform footprint**
- Traffic is served through a federated network of edge locations and core data centers across multiple regions.
- Requests automatically route to the closest healthy location, and capacity can shift between partners for failover.

**Providers & transparency**
- We manage the network stack internally and integrate with several cloud + carrier-neutral facilities.
- Specific VPS or bare-metal providers are not disclosed publicly so we can rotate infrastructure without notice.
- The goal is consistent performance, not reliance on a single vendor.

**Deep dives**
- Architecture diagrams, data-flow notes, and compliance mappings live in our reference architecture docs: ({reference_doc_path})
- Let me know what scenario you're planning (e.g., latency, compliance, migration) and I can highlight the right section."""


def _get_designer_ai_responses() -> dict:
    """Returns a dictionary of common responses for fallback when AI is not available."""
    return {
        "portfolio": {
            "keywords": ["portfolio", "structure", "layout", "case study", "project"],
            "response": """Great question about portfolios! Here are some best practices:

**Portfolio Structure:**
- Start with your strongest work
- Group projects by category or collection
- Include 3-5 high-quality images per project
- Add brief descriptions explaining your process

**On GlobalDesignerHub:**
- Use Collections to group related projects
- Add descriptive captions to each image
- Tag your work by category for easy discovery

For more details, check out: (/docs/designers/portfolio-layouts)"""
        },
        "upload": {
            "keywords": ["upload", "image", "size", "format", "video"],
            "response": """Here's how to handle media on GlobalDesignerHub:

**Image Guidelines:**
- Recommended size: 1920x1080px or larger
- Formats: JPG, PNG, WebP
- Max file size: 10MB per image
- For best quality, use high-resolution images

**Video Guidelines:**
- Formats: MP4, WebM
- Max file size: 100MB
- Recommended resolution: 1080p

**Upload Process:**
1. Go to Dashboard → Designs
2. Click "New Design"
3. Upload your images/videos
4. Add titles, descriptions, and tags

Need more help? See: (/docs/designers/media-guidelines)"""
        },
        "profile": {
            "keywords": ["profile", "create", "setup", "account"],
            "response": """Setting up your GlobalDesignerHub profile is easy:

**Getting Started:**
1. Sign up for an account
2. Complete your designer profile
3. Add a profile image and bio
4. Start uploading your work

**Profile Tips:**
- Use a professional photo
- Write a compelling bio highlighting your expertise
- Add your location and specialization
- Link your social media accounts

Learn more: (/docs/designers/getting-started)"""
        },
        "api": {
            "keywords": ["api", "integration", "embed", "sync", "webhook"],
            "response": """GlobalDesignerHub offers a REST API for integrations:

**API Features:**
- Portfolio management (list, create, update projects)
- Media uploads
- Collection management
- Authentication via API keys

**Getting Started:**
- API Overview: (/docs/api/overview)
- Authentication: (/docs/api/auth)
- Portfolio API: (/docs/api/portfolios)

**Embedding:**
You can embed your GDH portfolio on your own website using our embed widgets.

For developers: (/docs/api/overview)"""
        },
        "infrastructure": {
            "keywords": [
                "infrastructure",
                "server",
                "servers",
                "hosting",
                "uptime",
                "redundancy",
                "datacenter",
                "data center",
                "vps",
                "provider",
                "providers",
                "cloud",
                "architecture",
                "reference architecture",
                "network",
                "scalability",
            ],
            "response": _build_infrastructure_response(),
        },
        "default": {
            "response": """I'm here to help with design portfolios and GlobalDesignerHub!

I can assist with:
- Portfolio structure and layouts
- Uploading and organizing your work
- Using GDH features
- API and integration questions

Try asking:
- "How do I create my portfolio?"
- "What image size should I upload?"
- "How do I use the API?"

Or check out our docs: (/docs/designers/getting-started)"""
        }
    }


def _get_ai_response_fallback(message: str, context_page: str = "") -> str:
    """Enhanced fallback response with FAQ integration."""
    message_lower = message.lower()
    
    # Comprehensive FAQ-based responses
    faq_responses = {
        "portfolio": {
            "keywords": ["portfolio", "showcase", "projects", "work samples", "display work"],
            "response": """**Building a Strong Portfolio** 🎨

Your portfolio should include:
• Professional bio + headshot
• 6-10 best projects (quality over quantity)
• Detailed case studies showing your process
• Before/after visuals demonstrating impact
• Client testimonials for credibility
• Clear contact or booking link

**Pro tips:**
- Update every 3 months
- Use high-quality images (1200-1600px, under 250KB)
- Focus on storytelling and results
- Keep navigation simple and intuitive

Need help with specific aspects? Just ask!"""
        },
        "registration": {
            "keywords": ["register", "sign up", "create account", "join", "how to register"],
            "response": """**Joining GlobalDesignerHub** 👋

To register as a designer:
1. Click "Start Free Trial" or "Sign Up" in the navigation
2. Fill out your profile information
3. Add your portfolio link (optional but recommended)
4. Choose a subscription plan when you're ready (optional)
5. Complete verification

**What you get:**
✅ Personal designer profile
✅ Project showcase capabilities
✅ Access to community forum
✅ Designer AI assistant
✅ Collaboration opportunities

Your profile is reviewed privately before going public. Ready to start? Click "Sign Up" in the top menu!"""
        },
        "website_slow": {
            "keywords": ["slow", "loading", "performance", "speed", "fast", "optimize"],
            "response": """**Improving Website Performance** ⚡

Common causes of slow portfolios:
1. **Large images** - Compress to under 250KB
2. **Heavy videos** - Use lazy loading
3. **Unused code** - Minify CSS/JavaScript
4. **Poor hosting** - Consider upgrading

**Quick fixes:**
✅ Use WEBP format for images
✅ Enable caching
✅ Lazy-load media below the fold
✅ Use a CDN for static assets
✅ Remove unused plugins/libraries

**Testing tools:**
- Google PageSpeed Insights
- GTmetrix
- Lighthouse (Chrome DevTools)

Want specific optimization help? Let me know what's slowing you down!"""
        },
        "security": {
            "keywords": ["secure", "security", "hack", "ssl", "https", "password", "protect"],
            "response": """**Website Security Best Practices** 🔒

Essential security measures:

**Access Control:**
• Use strong, unique passwords
• Enable two-factor authentication (2FA)
• Limit login attempts

**Technical Protection:**
• Enable HTTPS with SSL certificate (free via Let's Encrypt)
• Keep all software updated
• Remove unused plugins
• Use trusted hosting

**Monitoring:**
• Regular malware scans
• Monitor suspicious activity
• Set up security plugins (Wordfence, Sucuri)
• Maintain regular backups

**Remember:** A hacked portfolio damages your professional reputation. Security is essential!

Need help setting up specific security features?"""
        },
        "responsive": {
            "keywords": ["responsive", "mobile", "tablet", "device", "breakpoint", "adaptive"],
            "response": """**Creating Responsive Designs** 📱

**Best practices:**
1. **Mobile-first approach** - Design for small screens first
2. **Flexible layouts** - Use CSS Grid or Flexbox
3. **Fluid units** - Use %, vw, rem instead of fixed pixels
4. **Responsive images** - Implement srcset for multiple sizes

**Standard breakpoints:**
• Mobile: 320-480px
• Tablet: 768-1024px
• Desktop: 1200px+

**Testing:**
• Chrome DevTools device mode
• Real device testing
• Both portrait and landscape orientations

**Common issues:**
- Fixed-width elements
- Non-responsive images
- Missing media queries
- Absolute positioning conflicts

Need help with a specific responsive design challenge?"""
        },
        "client": {
            "keywords": ["client", "revision", "payment", "contract", "scope", "unlimited"],
            "response": """**Managing Client Relationships** 💼

**Handling unlimited revision requests:**
1. Set clear limits in your contract (2-3 rounds typical)
2. Define what counts as a revision
3. Charge for additional rounds
4. Document all requests

**Essential contract elements:**
✓ Scope of work & deliverables
✓ Timeline & milestones
✓ Revision limits
✓ Payment schedule (50% upfront common)
✓ Copyright & usage rights
✓ Cancellation terms

**Pricing additional work:**
• Hourly rate for extra revisions
• Revision packages (e.g., 3 for $XXX)
• Clear communication about boundaries

**Pro tip:** Clear boundaries protect both your time and the client relationship.

Need help with a specific client situation?"""
        },
        "ui_design": {
            "keywords": ["ui", "user interface", "design principles", "visual design", "layout"],
            "response": """**UI Design Principles** 🎨

**Essential principles:**
1. **Consistency** - Uniform patterns and spacing
2. **Visual Hierarchy** - Clear emphasis on important elements
3. **Spacing & Alignment** - Proper whitespace and grid-based layouts
4. **Intuitive Navigation** - Clear menu structure and CTAs
5. **Accessibility** - High contrast, keyboard navigation, screen reader support
6. **Responsiveness** - Mobile-first, flexible grids

**Design process:**
• Start with low-fidelity wireframes
• Create high-fidelity mockups
• Build interactive prototypes
• Test with real users
• Iterate based on feedback

**Popular tools:**
Figma, Adobe XD, Sketch, Miro, Framer

What specific aspect of UI design would you like to explore?"""
        },
        "backup": {
            "keywords": ["backup", "restore", "recovery", "save", "data loss"],
            "response": """**Website Backup Strategy** 💾

**Backup frequency:**
• Static sites: Weekly
• Dynamic sites: Daily automated backups
• Before major updates: Always!

**What to backup:**
✓ Website files
✓ Database
✓ Media/uploads
✓ Configuration files

**Best practices:**
• Keep 30-day backup history
• Store in multiple locations:
  - Cloud storage (Google Drive, Dropbox)
  - Offline external drive
  - Hosting provider backups
• Test restore process regularly

**Recommended tools:**
- UpdraftPlus (WordPress)
- cPanel backup tools
- Git for code versioning
- Automated backup services

**Remember:** The best backup is the one you never need but always have!

Need help setting up automated backups?"""
        },
        "community": {
            "keywords": ["community", "forum", "networking", "collaborate", "connect", "designers"],
            "response": """**Designer Community Benefits** 👥

**Why join our community:**
🤝 **Networking** - Connect with designers globally
💡 **Learning** - Get feedback and learn from others
💼 **Opportunities** - Job leads and collaborations
🎨 **Inspiration** - See diverse approaches
🛠️ **Resources** - Templates, tools, and knowledge
❤️ **Support** - Motivation and advice

**How to participate:**
• Share your work in Portfolio & Showcase
• Ask questions in appropriate categories
• Give constructive feedback to others
• Join design challenges
• Share tutorials and tips

**Community guidelines:**
- Be respectful and constructive
- Give credit to original creators
- No plagiarism
- Keep discussions professional

**Visit our forum:** /community/forum/

Ready to connect with fellow designers?"""
        },
        "troubleshooting": {
            "keywords": ["error", "not working", "broken", "fix", "problem", "issue", "help"],
            "response": """**Common Issues & Solutions** 🛠️

**Images not loading?**
• Check file paths and extensions
• Verify image format (JPG, PNG, WEBP)
• Compress large files
• Check HTTPS/HTTP mixed content

**Contact form not working?**
• Verify SMTP settings
• Check form validation
• Test email server
• Check spam folder

**Layout broken on mobile?**
• Add responsive breakpoints
• Use flexible layouts (Grid/Flexbox)
• Test on real devices
• Check fixed-width elements

**Site not updating?**
• Clear cache (browser + server)
• Hard refresh (Ctrl+F5)
• Check file upload completed
• Verify deployment succeeded

**Need specific help?** Describe your issue in detail and I'll provide targeted solutions!"""
        },
        "tools": {
            "keywords": ["tools", "software", "figma", "adobe", "sketch", "xd", "photoshop"],
            "response": """**Popular Design Tools** 🛠️

**UI/UX Design:**
• Figma - Collaborative interface design
• Adobe XD - UI/UX and prototyping
• Sketch - Mac-based design tool
• Miro - Brainstorming and wireframing

**Graphic Design:**
• Adobe Photoshop - Image editing
• Adobe Illustrator - Vector graphics
• Canva - Quick designs and templates

**Prototyping:**
• Framer - Interactive prototypes
• InVision - Design collaboration
• Proto.io - Mobile prototyping

**Development:**
• Webflow - No-code web design
• VS Code - Code editor
• GitHub - Version control

**GlobalDesignerHub offers:**
Flexible subscriptions that unlock premium templates, community perks, and support.

Which tools are you interested in learning more about?"""
        },
        "pricing": {
            "keywords": ["price", "cost", "pricing", "rate", "charge", "fee", "payment"],
            "response": """**Design Pricing Guide** 💰

**Common pricing models:**

**Hourly Rate:**
• Beginners: $25-50/hour
• Mid-level: $50-100/hour
• Expert: $100-200+/hour

**Project-Based:**
• Logo design: $500-5,000
• Website design: $2,000-20,000
• App UI/UX: $5,000-50,000+

**Retainer:**
• Monthly ongoing work
• Guaranteed availability
• Usually discounted hourly rate

**Value-Based:**
• Price based on client ROI
• Higher risk, higher reward
• Best for experienced designers

**Tips for pricing:**
✓ Know your costs and desired profit
✓ Research market rates in your area
✓ Consider your experience level
✓ Factor in revision rounds
✓ Require deposit (50% common)

**GlobalDesignerHub subscriptions:**
• Basic plans: $4.99-$14.99/month
• Pro plans: $19.99-$29.99/month
• Includes premium templates and collaboration tools

Need help pricing a specific project type?"""
        },
        "collections": {
            "keywords": ["collection", "collections", "organize work", "group projects", "categorize", "categories"],
            "response": """**Organizing Work with Collections** 🗂️

Collections let you group related projects so visitors can browse your work by theme.

**How to use Collections:**
1. Go to Dashboard → Designs
2. Create a Collection (e.g., "Bridal 2025", "Streetwear", "Branding")
3. Add designs to the collection
4. Add a cover image and description

**Best practices:**
✅ Keep each collection focused on one theme or client
✅ Use clear, searchable titles
✅ Tag designs by category for easy discovery
✅ Order your strongest work first

Learn more: (/docs/designers/portfolio-layouts)

Want tips on which collections to feature first?"""
        },
        "branding": {
            "keywords": ["brand", "branding", "logo", "identity", "brand identity"],
            "response": """**Building a Strong Brand Identity** 🏷️

A cohesive brand makes you memorable and trustworthy.

**Core elements:**
• **Logo** - Simple, scalable, and recognizable
• **Color palette** - 2-3 primary colors + neutrals
• **Typography** - 1-2 typefaces used consistently
• **Voice & tone** - How you communicate with clients
• **Visual style** - Consistent imagery and layouts

**Tips:**
✅ Design your logo in vector format (SVG)
✅ Test the logo at small and large sizes
✅ Document your brand in a simple style guide
✅ Apply your brand consistently across your portfolio and proposals

Want help defining your color palette or typography?"""
        },
        "color": {
            "keywords": ["color", "colour", "palette", "color theory", "color scheme"],
            "response": """**Working with Color** 🎨

**Color theory basics:**
• **Complementary** - Opposite on the wheel (high contrast)
• **Analogous** - Neighbors on the wheel (harmonious)
• **Monochromatic** - One hue, varied shades (clean, elegant)
• **Triadic** - Three evenly spaced hues (balanced, vibrant)

**Building a palette:**
1. Pick one primary brand color
2. Add 1-2 accent colors for emphasis
3. Include neutrals (white, gray, near-black) for text and backgrounds
4. Check contrast for accessibility (4.5:1 minimum for text)

**Tools:**
Adobe Color, Coolors, Khroma, Figma color styles

Need help choosing colors for a specific project?"""
        },
        "typography": {
            "keywords": ["typography", "font", "fonts", "typeface", "lettering"],
            "response": """**Typography Essentials** 🔤

**Choosing fonts:**
• Limit to 1-2 typefaces per project
• Pair a display font (headlines) with a readable body font
• Ensure good legibility at all sizes

**Hierarchy tips:**
✅ Use size, weight, and spacing to guide the eye
✅ Keep body text 16px+ for readability
✅ Use generous line height (1.4-1.6) for body copy
✅ Limit line length to ~60-75 characters

**Reliable pairings:**
- Playfair Display + Source Sans
- Montserrat + Merriweather
- Inter + Inter (single-family, varied weights)

**Free sources:** Google Fonts, Fontshare

Want font recommendations for your brand style?"""
        },
        "proposal": {
            "keywords": ["proposal", "cover letter", "pitch", "client email", "outreach", "brief"],
            "response": """**Writing a Winning Proposal** ✉️

**Structure:**
1. **Greeting** - Personalize with the client's name
2. **Understanding** - Restate their goal so they feel heard
3. **Approach** - How you'll solve it (high level)
4. **Deliverables** - What they'll receive
5. **Timeline & price** - Clear, no surprises
6. **Call to action** - Next step to get started

**Tips:**
✅ Keep it concise — clients skim
✅ Lead with their outcome, not your process
✅ Show 1-2 relevant portfolio links
✅ Set clear revision limits up front

Want me to draft a proposal template you can reuse? Just share the project details!"""
        },
        "bio": {
            "keywords": ["bio", "about me", "introduction", "personal statement", "describe myself"],
            "response": """**Writing a Great Designer Bio** 🙋

A strong bio builds trust in seconds.

**A simple formula:**
1. **Who you are** + specialty ("Fashion designer focused on sustainable womenswear")
2. **What you do** for clients (the value/outcome)
3. **Proof** - experience, notable clients, or style
4. **Personality** - one human detail to be memorable
5. **Call to action** - how to work with you

**Tips:**
✅ Write in first or third person — stay consistent
✅ Keep it under 150 words for profiles
✅ Avoid clichés ("passionate," "detail-oriented")
✅ Update it as your focus evolves

Share a few details and I'll help you draft one!"""
        },
        "referral": {
            "keywords": ["referral", "invite", "refer", "earn tier", "ambassador", "reward"],
            "response": """**Referral Program — Invite & Earn** 🎁

Grow the community and earn rewards by inviting fellow designers!

**How it works:**
1. Find your invite link in this chat widget (Copy button)
2. Share it with designer friends and on social media
3. Earn tiers as people join through your link

**Tiers:**
🌱 **Starter** → 🚀 **Influencer** → ⭐ **Ambassador** → 👑 **Legend**

**Tips to get referrals:**
✅ Share your link in design communities and forums
✅ Add it to your email signature
✅ Mention it when collaborating with peers

Open this chat and use the Copy button to grab your invite link!"""
        },
        "subscription": {
            "keywords": ["subscription", "plan", "upgrade", "trial", "billing", "cancel", "downgrade"],
            "response": """**Subscriptions & Plans** 💳

**Managing your plan:**
1. Go to Dashboard → Subscription
2. View your current plan and billing history
3. Upgrade, downgrade, or cancel anytime
4. Manage payment methods securely

**What plans unlock:**
✅ Premium templates
✅ Larger media uploads
✅ Advanced collaboration tools
✅ Priority support

**Free trial:** Start with a trial to explore Pro features before committing.

**Cancelling:** You keep access until the end of your billing period — no surprise charges.

Need help choosing the right plan for your needs?"""
        },
        "seo": {
            "keywords": ["seo", "search ranking", "discoverable", "get found", "visibility", "rank"],
            "response": """**Getting Your Portfolio Found** 🔍

**On GlobalDesignerHub:**
✅ Complete your profile (bio, location, specialties)
✅ Tag every design with relevant categories/keywords
✅ Use descriptive titles and captions
✅ Organize work into well-named Collections

**General SEO tips:**
• Use clear, keyword-rich project titles
• Write alt text for images
• Keep load times fast (compressed images)
• Link your portfolio from social profiles
• Stay active — fresh work signals relevance

**Avoid:**
- Generic titles ("Project 1", "Untitled")
- Keyword stuffing
- Missing descriptions

Want help writing searchable titles for your projects?"""
        },
        "accessibility": {
            "keywords": ["accessibility", "accessible", "wcag", "contrast", "screen reader", "a11y"],
            "response": """**Designing for Accessibility** ♿

Accessible design reaches more people and is often legally required.

**Key checks:**
• **Contrast** - 4.5:1 for normal text, 3:1 for large text
• **Alt text** - Describe every meaningful image
• **Keyboard** - All interactions reachable without a mouse
• **Focus states** - Visible outlines on interactive elements
• **Text size** - 16px+ body, resizable without breaking layout

**Don't rely on color alone** to convey meaning (add icons/labels).

**Tools:**
WAVE, axe DevTools, Lighthouse, Stark (Figma plugin)

GlobalDesignerHub has an accessibility statement: (/policies/accessibility)

Want an accessibility checklist for your portfolio?"""
        },
        "techpack": {
            "keywords": ["techpack", "tech pack", "spec sheet", "manufacturer", "garment spec", "production sheet"],
            "response": """**Tech Packs for Production** 📐

A tech pack is the blueprint manufacturers use to produce your design accurately.

**A complete tech pack includes:**
• Technical flat sketches (front/back)
• Measurements and grading
• Materials, trims, and fabric details
• Colorways and Pantone references
• Construction and stitching notes
• Labels, tags, and packaging specs

**On GlobalDesignerHub:**
You can generate a tech pack directly from a design — look for the "Generate Tech Pack" option on your design page.

**Tips:**
✅ Be precise — ambiguity causes production errors
✅ Include callouts and annotations
✅ Keep a version for each sample round

Want help structuring a tech pack for a specific garment?"""
        },
        "getting_clients": {
            "keywords": ["find clients", "get hired", "freelance", "land work", "get work", "new clients"],
            "response": """**Finding Clients & Getting Hired** 🎯

**Build the foundation:**
✅ A polished, focused portfolio (quality over quantity)
✅ A clear niche — clients hire specialists
✅ Testimonials and case studies for credibility

**Where to find work:**
• Your network and past clients (referrals convert best)
• Design communities and forums
• Social media (share work consistently)
• Freelance platforms (to start building reviews)
• Cold outreach with a tailored proposal

**Convert leads:**
- Respond quickly and professionally
- Ask about their goals before pitching
- Send a clear proposal with scope and price

Want help with outreach messages or a proposal template?"""
        },
        "feedback": {
            "keywords": ["feedback", "critique", "review my", "improve my work", "evaluate my"],
            "response": """**Getting Useful Feedback** 🗣️

Feedback accelerates growth — when you ask the right way.

**How to ask:**
1. Share context (goal, audience, constraints)
2. Ask specific questions ("Is the hierarchy clear?")
3. Request both strengths and improvements
4. Avoid leading questions

**Where to get it on GDH:**
• Post in the community forum: /community/forum/
• Join design challenges
• Exchange critiques with peers

**Receiving feedback well:**
✅ Listen without defending
✅ Look for patterns across multiple opinions
✅ Decide what serves the project goal — not every note applies

Want me to review the description or structure of a specific project?"""
        },
        "social_media": {
            "keywords": ["instagram", "social media", "promote", "followers", "marketing my", "share my portfolio"],
            "response": """**Promoting Your Work on Social Media** 📣

**Strategy:**
✅ Pick 1-2 platforms and post consistently
✅ Show process, not just final results (reels, time-lapses)
✅ Use relevant, specific hashtags
✅ Engage — comment and connect, don't just broadcast

**Content ideas:**
• Before/after transformations
• Behind-the-scenes of your process
• Client results and testimonials
• Tips and mini-tutorials
• New portfolio pieces with a link

**Tips:**
- Add your portfolio link in your bio
- Cross-post to your GlobalDesignerHub profile
- Maintain a consistent visual style (your brand!)

Want a simple weekly posting plan?"""
        }
    }
    
    # Check FAQ responses first
    for category, data in faq_responses.items():
        for keyword in data["keywords"]:
            if keyword in message_lower:
                return data["response"]
    
    # Fallback to original responses
    responses = _get_designer_ai_responses()
    for key, data in responses.items():
        if key == "default":
            continue
        for keyword in data["keywords"]:
            if keyword in message_lower:
                return data["response"]
    
    # Default friendly response
    return """Hi! I'm Designer AI, your creative assistant. 👋

I can help you with:
🎨 **Portfolio advice** - Building and showcasing your work
🌐 **Website help** - Performance, security, troubleshooting
💻 **Design tips** - UI/UX principles and best practices
👥 **Community** - Connecting with other designers
💼 **Client relations** - Contracts, pricing, communication
🛠️ **Tools & software** - Recommendations and tutorials

**Quick actions:**
• "How do I register?" - Sign up guidance
• "Portfolio tips" - Build a strong showcase
• "Website slow" - Performance optimization
• "Responsive design" - Mobile-first development
• "Client revisions" - Managing scope

What would you like to know about?"""


@require_POST
@requires_csrf_token
def designer_ai_chat(request):
    """
    API endpoint for Designer AI chat with RAG, session management, and error handling.
    Accepts POST requests with JSON body:
    {
        "message": "user message",
        "context_page": "/dashboard/designs/",
        "current_url": "https://...",
        "language": "en"
    }
    """
    try:
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()
        context_page = data.get("context_page", "")
        current_url = data.get("current_url", "")
        language = data.get("language", "en")
        
        if not user_message:
            return JsonResponse({
                "success": False,
                "error": "Message is required"
            }, status=400)
        
        # Get or create session
        session_id = request.COOKIES.get("designer_ai_session")
        if session_id:
            try:
                session = DesignerAISession.objects.get(session_id=session_id)
            except DesignerAISession.DoesNotExist:
                session = None
        else:
            session = None
        
        if not session:
            session = DesignerAISession.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_id=str(uuid.uuid4()),
                language=language
            )

        # Get conversation history BEFORE saving current message (most recent 10, chronological order)
        history_qs = (
            DesignerAIMessage.objects.filter(session=session)
            .exclude(role="system")
            .order_by("-created_at")[:10]
        )
        history_messages = list(reversed(history_qs))

        # Build system prompt for designer platform
        system_prompt = _get_designer_ai_system_prompt()
        
        # Add context about current page
        if context_page:
            context_info = f"\n\nUser is currently on page: {context_page}"
            if "dashboard" in context_page:
                context_info += "\nThey are in the dashboard area."
            if "design" in context_page:
                context_info += "\nThey are working with designs."
            if "collection" in context_page:
                context_info += "\nThey are working with collections."
            system_prompt += context_info
        
        # RAG: Retrieve relevant documentation
        rag_docs = []
        try:
            rag_docs = list(DocPage.objects.filter(
                published=True,
                language=language
            ).filter(
                Q(content__icontains=user_message) |
                Q(title__icontains=user_message) |
                Q(tags__icontains=user_message)
            )[:3])
        except Exception as e:
            if settings.DEBUG:
                print(f"RAG error: {e}")
        
        # Build messages with history
        messages = [{"role": "system", "content": system_prompt}]

        # Add RAG context if found
        if rag_docs:
            rag_context = "\n\n--- Documentation Context ---\n\n"
            rag_context += "\n\n---\n\n".join(
                f"Title: {doc.title}\nContent: {doc.content[:500]}...\nLink: /docs/{doc.category}/{doc.slug}/"
                for doc in rag_docs
            )
            messages.append({"role": "system", "content": rag_context})

        # Add conversation history (chronological)
        for msg in history_messages:
            if msg.role in ["user", "assistant"]:
                messages.append({"role": msg.role, "content": msg.content})

        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Check if OpenAI is configured
        openai_api_key = (getattr(settings, "OPENAI_API_KEY", "") or "").strip()
        use_openai = bool(openai_api_key)

        ai_response = None

        if use_openai:
            try:
                from ai_chat.services import build_openai_client

                client = build_openai_client(openai_api_key)
                response = client.chat.completions.create(
                    model=getattr(settings, "OPENAI_MODEL", "gpt-4o-mini"),
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                ai_response = response.choices[0].message.content
                logger.info("Designer AI: OpenAI response received for session %s", session.session_id)

            except ImportError:
                logger.warning("Designer AI: openai library not installed. Run: pip install openai")
            except Exception as e:
                logger.exception("Designer AI OpenAI error: %s", e)
        
        # Fallback to rule-based responses if OpenAI failed
        if not ai_response:
            logger.info("Designer AI: Using fallback response (OpenAI not available or failed)")
            ai_response = _get_ai_response_fallback(user_message, context_page)

        # Save user message (for history on next request)
        DesignerAIMessage.objects.create(
            session=session,
            role="user",
            content=user_message,
        )

        # Save assistant response
        DesignerAIMessage.objects.create(
            session=session,
            role="assistant",
            content=ai_response,
            metadata={"rag_sources": [doc.slug for doc in rag_docs] if rag_docs else []}
        )
        
        # Return response
        response = JsonResponse({
            "success": True,
            "response": ai_response,
            "session_id": str(session.session_id)
        })
        response.set_cookie("designer_ai_session", str(session.session_id), max_age=60*60*24*30)  # 30 days
        return response
        
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON"
        }, status=400)
    except Exception as e:
        if settings.DEBUG:
            import traceback
            print(f"🔥 AI ERROR: {e}")
            print(traceback.format_exc())
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=500)
        return JsonResponse({
            "success": False,
            "error": "An error occurred. Please try again."
        }, status=500)


def my_conversations(request):
    """View for displaying user's AI chat history."""
    if not request.user.is_authenticated:
        from django.shortcuts import redirect
        return redirect("login")
    
    sessions = DesignerAISession.objects.filter(user=request.user).order_by("-created_at")[:50]
    
    return render(request, "designer_portfolio/my_conversations.html", {
        "sessions": sessions
    })


# ---------------- User-to-User Messenger ----------------

def _user_has_designer_profile(user):
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    return DesignerProfile.objects.filter(user=user).exists()


def _designer_search_results(query, exclude_user_ids, limit, exclude_frozen=True):
    qs = (
        DesignerProfile.objects.filter(user__is_active=True)
        .exclude(user_id__in=exclude_user_ids)
        .select_related("user")
    )
    if exclude_frozen:
        qs = qs.exclude(user__subscription__status="frozen")
    if query:
        qs = qs.filter(
            Q(user__username__icontains=query)
            | Q(user__first_name__icontains=query)
            | Q(user__last_name__icontains=query)
            | Q(specialization__icontains=query)
            | Q(location__icontains=query)
            | Q(city__icontains=query)
            | Q(country__icontains=query)
        )
    return list(qs.order_by("-created_at")[:limit])


def _get_or_create_conversation(user_a, user_b):
    """Return (conversation, created) with canonical user1/user2 order (user1.id <= user2.id)."""
    if user_a.pk == user_b.pk:
        raise ValueError("Cannot create conversation with self")
    u1, u2 = (user_a, user_b) if user_a.pk < user_b.pk else (user_b, user_a)
    conv, created = ChatConversation.objects.get_or_create(
        user1=u1, user2=u2, defaults={}
    )
    return conv, created


@login_required
def messenger_list(request):
    """List conversations for the current user."""
    can_use, reason, redirect_view = user_can_use_messenger(request.user)
    if not can_use:
        messages.info(request, reason)
        return redirect(redirect_view or "designer_about_me")

    messenger_unavailable = False
    messenger_unavailable_message = ""
    convs = []
    try:
        message_prefetch = Prefetch(
            "messages",
            queryset=ChatMessage.objects.select_related("sender").order_by("-created_at"),
            to_attr="prefetched_messages",
        )
        convs = list(
            ChatConversation.objects.filter(
                Q(user1=request.user) | Q(user2=request.user)
            )
            .select_related("user1", "user2")
            .prefetch_related(message_prefetch)
            .order_by("-updated_at")
        )
        # Annotate last message and other user for display
        existing_partner_ids = []
        for c in convs:
            prefetched = getattr(c, "prefetched_messages", [])
            c._last_msg = prefetched[0] if prefetched else None
            c._other_user = c.other_user(request.user)
            existing_partner_ids.append(c._other_user.id)
    except (OperationalError, ProgrammingError) as e:
        # Messenger tables missing (migration not applied on production)
        logger.warning("Messenger tables may be missing: %s. Run: python manage.py migrate", e)
        messenger_unavailable = True
        messenger_unavailable_message = "Messenger is being set up. Please try again in a few minutes."
        existing_partner_ids = []
    except Exception as e:
        err_str = str(e).lower()
        if "chatconversation" in err_str or "chat_message" in err_str or "does not exist" in err_str or "no such table" in err_str:
            logger.warning("Messenger tables may be missing: %s. Run: python manage.py migrate", e)
            messenger_unavailable = True
            messenger_unavailable_message = "Messenger is being set up. Please try again in a few minutes."
            existing_partner_ids = []
        else:
            raise

    search_query = (request.GET.get("q") or "").strip()
    if search_query:
        designer_results_title = "Search results"
        designer_results = _designer_search_results(
            search_query, {request.user.id}, limit=12
        )
    else:
        designer_results_title = "Suggested designers"
        designer_results = _designer_search_results(
            "", {request.user.id}, limit=6
        )

    return render(
        request,
        "designer_portfolio/messenger_list.html",
        {
            "conversations": convs,
            "messenger_unavailable": messenger_unavailable,
            "messenger_unavailable_message": messenger_unavailable_message,
            "designer_search_query": search_query,
            "designer_results_title": designer_results_title,
            "designer_results": designer_results,
            "existing_conversation_user_ids": existing_partner_ids,
        },
    )


@login_required
def messenger_thread(request, conversation_id):
    """Show one conversation and its messages; accept POST to send a new message."""
    can_use, reason, redirect_view = user_can_use_messenger(request.user)
    if not can_use:
        messages.info(request, reason)
        return redirect(redirect_view or "designer_about_me")

    try:
        conv = get_object_or_404(
            ChatConversation.objects.select_related("user1", "user2"),
            pk=conversation_id,
        )
    except (OperationalError, ProgrammingError):
        messages.info(request, "Messenger is being set up. Please try again in a few minutes.")
        return redirect("messenger_list")
    if request.user not in (conv.user1, conv.user2):
        raise Http404("Not a participant in this conversation")

    try:
        messages_list = list(
            conv.messages.select_related("sender").order_by("created_at")
        )
    except (OperationalError, ProgrammingError):
        messages.info(request, "Messenger is being set up. Please try again in a few minutes.")
        return redirect("messenger_list")

    conv.messages.exclude(sender=request.user).filter(read_at__isnull=True).update(read_at=timezone.now())

    if request.method == "POST":
        body = (request.POST.get("body") or "").strip()
        if body:
            prohibited, err_msg = message_contains_prohibited_content(body)
            if prohibited:
                messages.error(request, err_msg)
                # Freeze account for attempting to share contact info / external links
                try:
                    sub = request.user.subscription
                    if sub.status != "frozen":
                        sub.status = "frozen"
                        sub.save(update_fields=["status", "updated_at"])
                        messages.error(
                            request,
                            "Your account has been frozen due to this policy violation. "
                            "Please contact support if you believe this is an error.",
                        )
                except (UserSubscription.DoesNotExist, AttributeError):
                    pass
            else:
                try:
                    msg = ChatMessage.objects.create(
                        conversation=conv, sender=request.user, body=body
                    )
                    ChatConversation.objects.filter(pk=conv.pk).update(updated_at=timezone.now())
                    messages_list.append(msg)
                    messages.success(request, "Message sent.")
                    return redirect("messenger_thread", conversation_id=conv.pk)
                except (OperationalError, ProgrammingError):
                    messages.info(request, "Messenger is being set up. Please try again in a few minutes.")
                    return redirect("messenger_list")
        else:
            messages.error(request, "Message cannot be empty.")
    other = conv.other_user(request.user)
    return render(
        request,
        "designer_portfolio/messenger_thread.html",
        {
            "conversation": conv,
            "messages_list": messages_list,
            "other_user": other,
        },
    )


@login_required
def messenger_start(request, user_id):
    """Start or open a conversation with another user. Redirects to thread."""
    can_use, reason, redirect_view = user_can_use_messenger(request.user)
    if not can_use:
        messages.info(request, reason)
        return redirect(redirect_view or "designer_about_me")

    other = get_object_or_404(User, pk=user_id, is_active=True)
    if other.pk == request.user.pk:
        messages.error(request, "You cannot message yourself.")
        return redirect("messenger_list")
    if not DesignerProfile.objects.filter(user=other).exists():
        messages.error(request, "This designer is not available for messaging yet.")
        return redirect("messenger_list")
    try:
        if getattr(other.subscription, "status", None) == "frozen":
            messages.error(request, "This designer is not available for messaging.")
            return redirect("messenger_list")
    except (UserSubscription.DoesNotExist, AttributeError):
        pass
    try:
        conv, _ = _get_or_create_conversation(request.user, other)
        return redirect("messenger_thread", conversation_id=conv.pk)
    except (OperationalError, ProgrammingError):
        messages.info(request, "Messenger is being set up. Please try again in a few minutes.")
        return redirect("messenger_list")


# ---------------- Enhanced Forum Views ----------------
class ForumIndexView(TemplateView):
    """Main forum index showing categories and recent activity"""
    template_name = "designer_portfolio/forum/forum_index.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get active categories with stats
        categories = ForumCategory.objects.filter(is_active=True).prefetch_related('topics')
        
        # Get recent topics across all categories
        recent_topics = ForumTopic.objects.filter(
            is_active=True, 
            category__is_active=True
        ).select_related('author', 'category').order_by('-last_activity')[:5]
        
        # Get featured topics
        featured_topics = ForumTopic.objects.filter(
            is_featured=True, 
            is_active=True,
            category__is_active=True
        ).select_related('author', 'category')[:3]
        
        # Get forum stats
        total_topics = ForumTopic.objects.filter(is_active=True).count()
        total_posts = ForumPost.objects.filter(is_active=True).count()
        total_members = User.objects.filter(is_active=True).count()
        
        context.update({
            'categories': categories,
            'recent_topics': recent_topics,
            'featured_topics': featured_topics,
            'total_topics': total_topics,
            'total_posts': total_posts,
            'total_members': total_members,
        })
        
        return context


class ForumCategoryView(ListView):
    """View topics in a specific category"""
    model = ForumTopic
    template_name = "designer_portfolio/forum/forum_category.html"
    context_object_name = "topics"
    paginate_by = 20
    
    def get_queryset(self):
        self.category = get_object_or_404(ForumCategory, slug=self.kwargs['slug'], is_active=True)
        queryset = ForumTopic.objects.filter(
            category=self.category, 
            is_active=True
        ).select_related('author', 'last_post__author').order_by('-is_pinned', '-last_activity')
        
        # Search functionality
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) | 
                Q(content__icontains=search_query) |
                Q(tags__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        context['search_query'] = self.request.GET.get('search', '')
        return context


class ForumTopicView(DetailView):
    """View a specific topic with posts"""
    model = ForumTopic
    template_name = "designer_portfolio/forum/forum_topic.html"
    context_object_name = "topic"
    
    def get_queryset(self):
        return ForumTopic.objects.filter(
            is_active=True,
            category__is_active=True
        ).select_related('category', 'author')
    
    def get_object(self):
        topic = super().get_object()
        # Increment view count
        topic.view_count = F('view_count') + 1
        topic.save(update_fields=['view_count'])
        topic.refresh_from_db()
        return topic
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get posts with replies
        posts = ForumPost.objects.filter(
            topic=self.object,
            is_active=True,
            parent=None  # Only top-level posts
        ).select_related('author').prefetch_related(
            'replies__author', 'likes'
        ).order_by('created_at')
        
        # Pagination for posts
        paginator = Paginator(posts, 10)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Check if user has bookmarked this topic
        user_bookmarked = False
        if self.request.user.is_authenticated:
            user_bookmarked = ForumBookmark.objects.filter(
                user=self.request.user,
                topic=self.object
            ).exists()
        
        context.update({
            'posts': page_obj,
            'page_obj': page_obj,
            'user_bookmarked': user_bookmarked,
        })
        
        return context


class ForumCreateTopicView(LoginRequiredMixin, CreateView):
    """Create a new forum topic"""
    model = ForumTopic
    template_name = "designer_portfolio/forum/forum_create_topic.html"
    fields = ['title', 'content', 'category', 'tags']
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        response = super().form_valid(form)
        
        # Update user's topic count
        profile, created = ForumUserProfile.objects.get_or_create(user=self.request.user)
        profile.topic_count = F('topic_count') + 1
        profile.save()
        
        messages.success(self.request, 'Topic created successfully!')
        return response
    
    def get_success_url(self):
        return reverse('forum_topic_detail', kwargs={'slug': self.object.slug})


class ForumCreatePostView(LoginRequiredMixin, CreateView):
    """Create a new post in a topic"""
    model = ForumPost
    template_name = "designer_portfolio/forum/create_post.html"
    fields = ['content']
    
    def dispatch(self, request, *args, **kwargs):
        self.topic = get_object_or_404(ForumTopic, slug=kwargs['topic_slug'], is_active=True)
        if self.topic.is_locked and not request.user.is_staff:
            messages.error(request, 'This topic is locked.')
            return redirect('forum_topic_detail', slug=self.topic.slug)
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.topic = self.topic
        
        # Handle parent post for replies
        parent_id = self.request.POST.get('parent_id')
        if parent_id:
            form.instance.parent = get_object_or_404(ForumPost, id=parent_id, topic=self.topic)
        
        response = super().form_valid(form)
        
        # Update topic's last activity
        self.topic.last_activity = timezone.now()
        self.topic.last_post = form.instance
        self.topic.save()
        
        # Update user's post count
        profile, created = ForumUserProfile.objects.get_or_create(user=self.request.user)
        profile.post_count = F('post_count') + 1
        profile.save()
        
        messages.success(self.request, 'Post created successfully!')
        return response
    
    def get_success_url(self):
        return reverse('forum_topic_detail', kwargs={'slug': self.topic.slug})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['topic'] = self.topic
        
        # Handle reply to specific post
        parent_id = self.request.GET.get('reply_to')
        if parent_id:
            try:
                context['parent_post'] = ForumPost.objects.get(id=parent_id, topic=self.topic)
            except ForumPost.DoesNotExist:
                pass
        
        return context


@login_required
def forum_bookmark_toggle(request, topic_slug):
    """Toggle bookmark for a topic"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    topic = get_object_or_404(ForumTopic, slug=topic_slug, is_active=True)
    bookmark, created = ForumBookmark.objects.get_or_create(
        user=request.user,
        topic=topic
    )
    
    if not created:
        bookmark.delete()
        bookmarked = False
    else:
        bookmarked = True
    
    return JsonResponse({
        'bookmarked': bookmarked,
        'message': 'Topic bookmarked!' if bookmarked else 'Bookmark removed!'
    })


@login_required
def forum_post_like(request, post_id):
    """Like/unlike a forum post"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    post = get_object_or_404(ForumPost, id=post_id, is_active=True)
    like, created = ForumLike.objects.get_or_create(
        user=request.user,
        post=post
    )
    
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    
    like_count = post.likes.count()
    
    return JsonResponse({
        'liked': liked,
        'like_count': like_count,
        'message': 'Post liked!' if liked else 'Like removed!'
    })


@staff_member_required
def forum_post_toggle_solution(request, post_id):
    """Mark/unmark post as solution (staff only)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    post = get_object_or_404(ForumPost, id=post_id, is_active=True)
    
    # Remove solution status from other posts in the topic
    if not post.is_solution:
        ForumPost.objects.filter(topic=post.topic).update(is_solution=False)
        post.is_solution = True
        message = 'Post marked as solution!'
    else:
        post.is_solution = False
        message = 'Solution status removed!'
    
    post.save()
    
    return JsonResponse({
        'is_solution': post.is_solution,
        'message': message
    })


class ForumSearchView(TemplateView):
    """Global forum search"""
    template_name = "designer_portfolio/forum/forum_search.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        search_query = self.request.GET.get('q', '').strip()
        search_type = self.request.GET.get('type', 'all')
        
        if search_query:
            if search_type == 'topics' or search_type == 'all':
                topics = ForumTopic.objects.filter(
                    Q(title__icontains=search_query) |
                    Q(content__icontains=search_query) |
                    Q(tags__icontains=search_query),
                    is_active=True,
                    category__is_active=True
                ).select_related('author', 'category')[:20]
            else:
                topics = []
            
            if search_type == 'posts' or search_type == 'all':
                posts = ForumPost.objects.filter(
                    content__icontains=search_query,
                    is_active=True,
                    topic__is_active=True
                ).select_related('author', 'topic', 'topic__category')[:20]
            else:
                posts = []
        else:
            topics = []
            posts = []
        
        context.update({
            'search_query': search_query,
            'search_type': search_type,
            'topics': topics,
            'posts': posts,
            'total_results': len(topics) + len(posts),
        })
        
        return context


class GoogleReviewView(LoginRequiredMixin, TemplateView):
    template_name = "designer_portfolio/google_review.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["current_section"] = "reviews"
        return context
