# Generated for Documenso webhook handler (2026-04-25)
# Adds documenso_doc_id to Deal so webhook events can match to a Deal row.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('broker_ops', '0012_consent_forensic_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='deal',
            name='documenso_doc_id',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                help_text='Documenso document ID. Webhook payload key for matching.',
                max_length=64,
            ),
        ),
    ]
