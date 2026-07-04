"""
Idempotent seed for community feature pack starter content.

Loads:
  - Three upcoming Events (webinar, workshop, design jam)
  - Two Emerging Talent features (published)

Usage:
    python3 manage.py seed_community_starter_content

Re-running is safe: rows are matched by slug and updated in place.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from marketing.models import EmergingTalentFeature, Event

STARTER_EVENTS = [
    {
        "title": "Portfolio teardown · live",
        "kind": Event.Kind.WEBINAR,
        "summary": "Live teardown of three drden portfolios — what's working, what's hiding, what to fix this week.",
        "description_html": (
            "<p>Bring your portfolio link or just lurk. We'll review three "
            "real drden portfolios on screen — covering hierarchy of work, "
            "tech-pack pairing, and how to write a buyer-friendly about page. "
            "Q&A at the end.</p>"
            "<p><strong>Who it's for:</strong> fashion students, recent grads, "
            "self-taught designers building toward a first role.</p>"
        ),
        "starts_in_days": 7,
        "duration_minutes": 60,
        "timezone_label": "New York · ET",
        "host_name": "drden editorial",
        "host_bio": (
            "drden's editorial team curates Emerging Talent features and reviews "
            "thousands of portfolios a year."
        ),
        "is_virtual": True,
        "location": "Zoom",
        "capacity": 200,
    },
    {
        "title": "Tech pack basics · workshop",
        "kind": Event.Kind.WORKSHOP,
        "summary": "Hands-on: turn one of your concepts into a tech pack a factory could actually quote against.",
        "description_html": (
            "<p>A 90-minute working session. Bring one concept (sketch, mood "
            "board, garment photo) — leave with a tech pack draft, BOM "
            "started, and a feedback note from a working technical designer.</p>"
            "<p>We'll use drden's tech-pack templates so you walk away with "
            "something you can keep building on.</p>"
        ),
        "starts_in_days": 14,
        "duration_minutes": 90,
        "timezone_label": "London · BST",
        "host_name": "Priya M., technical designer",
        "host_bio": (
            "Priya has spent the last decade as a technical designer for "
            "European womenswear brands and teaches tech-pack craft at drden."
        ),
        "is_virtual": True,
        "location": "Zoom",
        "capacity": 60,
    },
    {
        "title": "Design jam · denim, 4-hour sprint",
        "kind": Event.Kind.DESIGN_JAM,
        "summary": "Four hours, one brief, the drden community. Pitch, design and submit a denim look in real time.",
        "description_html": (
            "<p>A live design jam: we drop a brief at the top of the hour, "
            "you have four hours to design a denim look (sketch, fabric "
            "story, BOM), and submit at the end. The drden editorial team "
            "shouts out favorites in the next newsletter.</p>"
            "<p><strong>What to bring:</strong> your favorite tools, a snack, "
            "and the willingness to ship something rough.</p>"
        ),
        "starts_in_days": 21,
        "duration_minutes": 240,
        "timezone_label": "Los Angeles · PT",
        "host_name": "drden community",
        "host_bio": "",
        "is_virtual": True,
        "location": "Discord stage",
        "capacity": None,
    },
]


STARTER_FEATURES = [
    {
        "title": "Capsule by Maya R.",
        "display_name": "Maya R.",
        "designer_portfolio_url": "https://example.com/maya-r-portfolio",
        "hero_image_url": "",
        "bio_html": (
            "<p>Maya is a senior at Parsons working at the intersection of "
            "tailoring and tech-wear. Her senior collection — built around "
            "deadstock Italian wool and 3D-knit panels — was featured in our "
            "Spring trend brief.</p>"
        ),
        "success_story_html": (
            "<p>Two weeks after her drden portfolio went live, Maya was invited "
            "to interview with a major NYC menswear brand for an associate "
            "designer role. The hiring manager mentioned the portfolio's "
            "tech-pack pairings as the reason.</p>"
        ),
        "ordering": 10,
    },
    {
        "title": "Ren Studio",
        "display_name": "Ren",
        "designer_portfolio_url": "https://example.com/ren-studio",
        "hero_image_url": "",
        "bio_html": (
            "<p>Ren is a self-taught designer based in Mexico City. Their "
            "small-batch womenswear line Ren Studio launched in 2025 and "
            "has been featured by independent buyers in the US and EU.</p>"
        ),
        "success_story_html": (
            "<p>After a feature in our Emerging Talent newsletter, Ren was "
            "approached by a Brooklyn boutique for a six-piece capsule that "
            "drops next quarter. Ren credits drden's brand-partnership pipeline "
            "for the introduction.</p>"
        ),
        "ordering": 20,
    },
]


class Command(BaseCommand):
    help = (
        "Seed (or refresh) the drden community feature pack with starter "
        "events and Emerging Talent features."
    )

    def handle(self, *args, **options):
        now = timezone.now()
        events_created = 0
        events_updated = 0

        for spec in STARTER_EVENTS:
            slug = slugify(spec["title"])[:220]
            starts_at = now + timedelta(days=spec["starts_in_days"])
            ends_at = starts_at + timedelta(minutes=spec["duration_minutes"])
            defaults = {
                "title": spec["title"],
                "kind": spec["kind"],
                "summary": spec["summary"],
                "description_html": spec["description_html"],
                "starts_at": starts_at,
                "ends_at": ends_at,
                "timezone_label": spec["timezone_label"],
                "host_name": spec["host_name"],
                "host_bio": spec["host_bio"],
                "is_virtual": spec["is_virtual"],
                "location": spec["location"],
                "capacity": spec["capacity"],
                "status": Event.Status.SCHEDULED,
            }
            _, was_created = Event.objects.update_or_create(
                slug=slug, defaults=defaults
            )
            if was_created:
                events_created += 1
            else:
                events_updated += 1

        features_created = 0
        features_updated = 0

        for spec in STARTER_FEATURES:
            slug = slugify(spec["title"])[:220]
            defaults = {
                "title": spec["title"],
                "display_name": spec["display_name"],
                "designer_portfolio_url": spec["designer_portfolio_url"],
                "hero_image_url": spec["hero_image_url"],
                "bio_html": spec["bio_html"],
                "success_story_html": spec["success_story_html"],
                "ordering": spec["ordering"],
                "is_published": True,
                "published_at": now,
            }
            _, was_created = EmergingTalentFeature.objects.update_or_create(
                slug=slug, defaults=defaults
            )
            if was_created:
                features_created += 1
            else:
                features_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded community starter content: "
                f"events ({events_created} created, {events_updated} updated), "
                f"features ({features_created} created, {features_updated} updated)."
            )
        )
