# Generated for the wholesale strategic pivot (2026-04-25)
# Adds CallbackTask -- the phone callback queue.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('broker_ops', '0006_deal_stages_events_calls'),
    ]

    operations = [
        migrations.CreateModel(
            name='CallbackTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('lead_id', models.CharField(blank=True, db_index=True, help_text='UUID/ID of the related PropertyLead or LeadProfile', max_length=64)),
                ('buyer_id', models.CharField(blank=True, db_index=True, help_text='UUID of the related InvestorBuyer', max_length=64)),
                ('contact_name', models.CharField(blank=True, max_length=200)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('priority', models.CharField(choices=[
                    ('urgent', 'Urgent (call within 2h)'),
                    ('high', 'High (call within 24h)'),
                    ('normal', 'Normal (call within 48h)'),
                    ('low', 'Low (when convenient)'),
                ], db_index=True, default='normal', max_length=10)),
                ('status', models.CharField(choices=[
                    ('pending', 'Pending'),
                    ('in_progress', 'In progress'),
                    ('done', 'Done'),
                    ('voicemail', 'Voicemail left'),
                    ('no_answer', 'No answer'),
                    ('invalid', 'Bad number'),
                    ('snoozed', 'Snoozed'),
                ], db_index=True, default='pending', max_length=20)),
                ('reason', models.TextField(blank=True, help_text='Why this callback was queued')),
                ('talking_points', models.TextField(blank=True, help_text='What to say -- pre-loaded by Hammer Knox')),
                ('disposition_notes', models.TextField(blank=True, help_text='What was said on the call')),
                ('source', models.CharField(default='manual', help_text='manual | imap_reply | sms_reply | inbound_call | etc.', max_length=50)),
                ('assigned_to', models.CharField(blank=True, help_text='Human or VA assigned -- empty = unclaimed', max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-priority', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='callbacktask',
            index=models.Index(fields=['status', 'priority', '-created_at'], name='broker_ops__status_pri_idx'),
        ),
        migrations.AddIndex(
            model_name='callbacktask',
            index=models.Index(fields=['assigned_to', 'status'], name='broker_ops__assigned_idx'),
        ),
    ]
