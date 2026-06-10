# Generated for POF collection flow (2026-04-25)
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('broker_ops', '0009_deal_audit_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='POFRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(db_index=True, max_length=64, unique=True)),
                ('status', models.CharField(
                    choices=[('invited', 'Invited (link sent)'),
                             ('submitted', 'POF submitted, pending review'),
                             ('approved', 'Approved -- buyer can receive deals'),
                             ('rejected', 'Rejected (insufficient or expired)'),
                             ('expired', 'POF older than 90 days; resubmit')],
                    db_index=True, default='invited', max_length=20)),
                ('pof_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12,
                                                    help_text='Amount documented on the POF letter')),
                ('pof_letter_url', models.CharField(blank=True, max_length=1024,
                                                     help_text='Path to uploaded POF document')),
                ('pof_letter_dated', models.DateField(blank=True, null=True,
                                                       help_text='Date on the POF letter (must be < 90d old at deal time)')),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('reviewer_notes', models.TextField(blank=True)),
                ('buyer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                             related_name='pof_requests',
                                             to='broker_ops.investorbuyer')),
            ],
            options={
                'ordering': ['-requested_at'],
            },
        ),
    ]
