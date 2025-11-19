from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("designer_portfolio", "0007_docpage_designeraisession_designeraimessage"),
    ]

    operations = [
        migrations.AlterField(
            model_name="brand",
            name="primary_color",
            field=models.CharField(default="#0E0E0F", max_length=7),
        ),
        migrations.AlterField(
            model_name="brand",
            name="secondary_color",
            field=models.CharField(default="#2A2A2C", max_length=7),
        ),
        migrations.AlterField(
            model_name="brand",
            name="accent_color",
            field=models.CharField(default="#D8B57A", max_length=7),
        ),
    ]
