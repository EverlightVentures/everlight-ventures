# Generated for the PEWC consent system (2026-04-25)
# Adds ConsentLedger -- TCPA Prior Express Written Consent records.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('broker_ops', '0007_callbacktask'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConsentLedger',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contact_type', models.CharField(
                    choices=[('seller', 'Seller'), ('buyer', 'Cash Buyer / Investor'),
                             ('wholesaler', 'JV Wholesaler'), ('title_company', 'Title Company'),
                             ('other', 'Other')],
                    db_index=True, max_length=20)),
                ('contact_name', models.CharField(max_length=200)),
                ('contact_email', models.EmailField(blank=True, db_index=True, max_length=254)),
                ('contact_phone', models.CharField(blank=True, db_index=True,
                                                    help_text='Normalized 10-digit US number',
                                                    max_length=20)),
                ('channels', models.JSONField(default=list,
                                               help_text='List of authorized channel codes from CHANNEL_CHOICES')),
                ('disclosure_text', models.TextField(
                    help_text='Exact disclosure text shown to the contact at consent time. NEVER edit retroactively.')),
                ('signature_text', models.CharField(
                    help_text='What the contact typed/checked as their signature',
                    max_length=200)),
                ('signature_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('signature_user_agent', models.TextField(blank=True)),
                ('consent_token', models.CharField(db_index=True,
                                                    help_text='Random token in the consent URL',
                                                    max_length=64, unique=True)),
                ('revoked', models.BooleanField(db_index=True, default=False)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('revoked_reason', models.CharField(blank=True, max_length=200)),
                ('revoked_via', models.CharField(blank=True,
                                                  help_text='STOP_sms | unsubscribe_email | revoke_form | request_phone',
                                                  max_length=50)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['contact_phone', 'revoked', '-created_at'],
                                 name='broker_ops__phone_active_idx'),
                    models.Index(fields=['contact_email', 'revoked', '-created_at'],
                                 name='broker_ops__email_active_idx'),
                ],
            },
        ),
    ]
