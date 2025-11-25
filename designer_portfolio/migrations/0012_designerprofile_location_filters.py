from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("designer_portfolio", "0011_problemreport"),
    ]

    operations = [
        migrations.AddField(
            model_name="designerprofile",
            name="region_area",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Broader area or territory label (e.g., West Coast, EMEA).",
                max_length=120,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="designerprofile",
            name="country",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="Country",
                max_length=120,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="designerprofile",
            name="state_province",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="State or province",
                max_length=120,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="designerprofile",
            name="county",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="County or district",
                max_length=120,
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="designerprofile",
            name="city",
            field=models.CharField(
                blank=True,
                db_index=True,
                default="",
                help_text="City or municipality",
                max_length=120,
            ),
            preserve_default=False,
        ),
    ]
