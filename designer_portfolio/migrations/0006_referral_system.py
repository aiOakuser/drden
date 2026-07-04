# Generated manually for referral system

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("designer_portfolio", "0005_add_referred_by"),
    ]

    operations = [
        migrations.CreateModel(
            name="ReferralTier",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.SlugField(unique=True)),
                ("name", models.CharField(max_length=80)),
                ("min_referrals", models.PositiveIntegerField()),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("benefits", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["sort_order", "min_referrals"],
            },
        ),
        migrations.CreateModel(
            name="UserReferralProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("referral_code", models.CharField(db_index=True, max_length=32, unique=True)),
                ("referral_joined_at", models.DateTimeField(blank=True, null=True)),
                ("referral_count", models.PositiveIntegerField(default=0, help_text="Denormalized count for fast leaderboard")),
                ("referral_points", models.PositiveIntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "current_tier",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="users",
                        to="designer_portfolio.referraltier",
                    ),
                ),
                (
                    "referred_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who referred this user via invite link",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="referrals_made",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referral_profile",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "User Referral Profile",
                "verbose_name_plural": "User Referral Profiles",
            },
        ),
        migrations.CreateModel(
            name="ReferralEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("referral_code", models.CharField(max_length=32)),
                ("source", models.CharField(blank=True, max_length=32, null=True)),
                ("ip_hash", models.CharField(blank=True, max_length=128, null=True)),
                ("user_agent_hash", models.CharField(blank=True, max_length=128, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "referred_user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referral_event",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "referrer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="referral_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="referralevent",
            index=models.Index(fields=["referrer", "-created_at"], name="refev_referrer_created_idx"),
        ),
        migrations.AddIndex(
            model_name="referralevent",
            index=models.Index(fields=["-created_at"], name="refev_created_idx"),
        ),
        migrations.RunPython(
            code=lambda apps, schema_editor: _seed_referral_tiers(apps),
            reverse_code=migrations.RunPython.noop,
        ),
    ]


def _seed_referral_tiers(apps):
    ReferralTier = apps.get_model("designer_portfolio", "ReferralTier")
    tiers = [
        {"code": "starter", "name": "Starter", "min_referrals": 1, "sort_order": 1},
        {"code": "influencer", "name": "Influencer", "min_referrals": 3, "sort_order": 2},
        {"code": "ambassador", "name": "Ambassador", "min_referrals": 7, "sort_order": 3},
        {"code": "legend", "name": "Legend", "min_referrals": 15, "sort_order": 4},
    ]
    for t in tiers:
        ReferralTier.objects.get_or_create(code=t["code"], defaults=t)
