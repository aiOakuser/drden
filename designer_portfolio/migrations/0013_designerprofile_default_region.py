from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("designer_portfolio", "0012_designerprofile_location_filters"),
    ]

    operations = [
        migrations.AlterField(
            model_name="designerprofile",
            name="region_area",
            field=models.CharField(
                blank=True,
                default="West Coast",
                help_text="Broader area or territory label (e.g., West Coast, EMEA).",
                max_length=120,
                db_index=True,
            ),
        ),
    ]
