from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("funnel", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="lead",
            name="product",
            field=models.CharField(
                choices=[
                    ("onyx", "Onyx POS"),
                    ("hivemind", "Hive Mind SaaS"),
                    ("dashboard", "Trading Watchtower"),
                ],
                max_length=20,
            ),
        ),
    ]
