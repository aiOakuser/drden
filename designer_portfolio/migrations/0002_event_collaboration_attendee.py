from datetime import date

from django.core.validators import MinValueValidator
from django.db import migrations, models
import django.db.models.deletion


def seed_newyork_event(apps, schema_editor):
    Event = apps.get_model("designer_portfolio", "Event")
    slug = "newyork-fashion-show"
    defaults = {
        "title": "New York Fashion Week",
        "description": (
            "A New York Fashion Week runway showcase highlighting emerging labels and creative partners. "
            "VolumeOne attendees are 12 designers. Submit collaboration requests to join the backstage team or RSVP "
            "to attend the show."
        ),
        "event_date": date(2026, 2, 11),
        "end_date": date(2026, 2, 16),
        "location": "New York City, NY",
        "venue": "Spring Studios",
        "attendee_capacity": 350,
        "collaboration_deadline": date(2026, 1, 20),
        "is_popup": True,
        "popup_order": 1,
    }
    Event.objects.update_or_create(slug=slug, defaults=defaults)


def unseed_newyork_event(apps, schema_editor):
    Event = apps.get_model("designer_portfolio", "Event")
    Event.objects.filter(slug="newyork-fashion-show").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("designer_portfolio", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="end_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="event",
            name="location",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="event",
            name="venue",
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name="event",
            name="attendee_capacity",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                validators=[MinValueValidator(1)],
                help_text="Optional headcount limit for attendee RSVPs.",
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="collaboration_deadline",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="Optional cutoff for collaboration requests.",
            ),
        ),
        migrations.CreateModel(
            name="EventAttendee",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("full_name", models.CharField(max_length=120)),
                ("email", models.EmailField(max_length=254)),
                ("company", models.CharField(blank=True, max_length=120)),
                ("title", models.CharField(blank=True, max_length=120)),
                ("ticket_count", models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])),
                ("notes", models.TextField(blank=True)),
                ("checked_in", models.BooleanField(default=False)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attendees",
                        to="designer_portfolio.event",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("event", "email")},
            },
        ),
        migrations.CreateModel(
            name="EventCollaboration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("full_name", models.CharField(max_length=120)),
                ("email", models.EmailField(max_length=254)),
                ("company", models.CharField(blank=True, max_length=120)),
                ("role", models.CharField(blank=True, max_length=120)),
                ("portfolio_url", models.URLField(blank=True)),
                ("message", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("new", "New"),
                            ("reviewed", "Reviewed"),
                            ("accepted", "Accepted"),
                            ("declined", "Declined"),
                        ],
                        default="new",
                        max_length=20,
                    ),
                ),
                ("is_contacted", models.BooleanField(default=False)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="collaboration_requests",
                        to="designer_portfolio.event",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "unique_together": {("event", "email")},
            },
        ),
        migrations.RunPython(seed_newyork_event, unseed_newyork_event),
    ]
