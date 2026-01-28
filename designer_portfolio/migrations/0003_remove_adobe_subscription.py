from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("designer_portfolio", "0002_event_collaboration_attendee"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="usersubscription",
            name="includes_adobe_access",
        ),
        migrations.DeleteModel(
            name="AdobeAccessLog",
        ),
        migrations.DeleteModel(
            name="UserAdobeSubscription",
        ),
        migrations.DeleteModel(
            name="AdobePackage",
        ),
        migrations.DeleteModel(
            name="AdobeProduct",
        ),
    ]
