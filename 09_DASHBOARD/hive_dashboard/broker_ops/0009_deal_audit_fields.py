# Generated for the wholesale audit fixes (2026-04-25)
# Adds EMD tracking, close_type, inspection, and title status fields to Deal.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('broker_ops', '0008_consentledger'),
    ]

    operations = [
        migrations.AddField(
            model_name='deal',
            name='earnest_money_deposit',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10,
                                       help_text='Buyer EMD held with title/attorney. 0 = none on file yet.'),
        ),
        migrations.AddField(
            model_name='deal',
            name='emd_status',
            field=models.CharField(blank=True, max_length=20,
                choices=[('pending', 'Pending receipt'), ('held', 'Held by title'),
                         ('refunded', 'Refunded to buyer'), ('forfeited', 'Forfeited to seller'),
                         ('applied_to_close', 'Applied to closing')],
                help_text='Lifecycle state of the earnest money'),
        ),
        migrations.AddField(
            model_name='deal',
            name='emd_received_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='deal',
            name='emd_held_by',
            field=models.CharField(blank=True, max_length=200,
                                    help_text='Name of title company / attorney holding EMD'),
        ),
        migrations.AddField(
            model_name='deal',
            name='close_type',
            field=models.CharField(default='assignment', max_length=20,
                choices=[('assignment', 'Contract assignment'),
                         ('double_close', 'A->B then B->C double close'),
                         ('subject_to', 'Subject-to existing financing'),
                         ('direct_purchase', 'We buy and hold')],
                help_text='How the deal will close. Drives template + funding requirements.'),
        ),
        migrations.AddField(
            model_name='deal',
            name='funder_name',
            field=models.CharField(blank=True, max_length=200,
                                    help_text='Transactional funder for double closes'),
        ),
        migrations.AddField(
            model_name='deal',
            name='inspection_status',
            field=models.CharField(default='not_started', max_length=20,
                choices=[('not_started', 'Not started'), ('scheduled', 'Scheduled'),
                         ('complete', 'Complete'), ('waived', 'Waived'),
                         ('failed', 'Failed -- terminated')]),
        ),
        migrations.AddField(
            model_name='deal',
            name='inspection_due_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='deal',
            name='inspection_notes',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='deal',
            name='title_company',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='deal',
            name='title_search_ordered_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='deal',
            name='title_clear',
            field=models.BooleanField(default=False,
                                       help_text='Title returned clear and marketable'),
        ),
    ]
