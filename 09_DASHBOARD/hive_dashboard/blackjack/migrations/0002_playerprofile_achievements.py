from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blackjack', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='playerprofile',
            name='achievements',
            field=models.JSONField(default=list),
        ),
    ]
