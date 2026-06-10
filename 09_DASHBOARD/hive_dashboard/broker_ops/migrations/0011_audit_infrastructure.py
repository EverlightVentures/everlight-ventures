# Audit infrastructure models (2026-04-25)
# BankReconciliation, RESPAAuditLog, InsurancePolicy, GBPListing,
# AgentRoster, TestimonialCollection -- one model per audit gap.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('broker_ops', '0010_pofrequest'),
    ]

    operations = [
        migrations.CreateModel(
            name='BankReconciliation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period_year', models.IntegerField(db_index=True)),
                ('period_month', models.IntegerField(db_index=True, help_text='1-12')),
                ('bank_account_label', models.CharField(default='primary_checking', max_length=100)),
                ('statement_balance', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('book_balance', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('reconciled_balance', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('in_transit_deposits', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('outstanding_checks', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('discrepancies_count', models.IntegerField(default=0)),
                ('discrepancies_notes', models.TextField(blank=True)),
                ('statement_pdf_url', models.CharField(blank=True, max_length=1024)),
                ('reconciled', models.BooleanField(db_index=True, default=False)),
                ('reconciled_at', models.DateTimeField(blank=True, null=True)),
                ('reconciled_by', models.CharField(blank=True, help_text='Rich / CPA name', max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-period_year', '-period_month'],
                'unique_together': {('period_year', 'period_month', 'bank_account_label')},
            },
        ),
        migrations.CreateModel(
            name='RESPAAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_type', models.CharField(
                    choices=[('referral', 'Referral fee'), ('birddog', 'Bird-dog finder fee'),
                             ('commission_split', 'Commission split (JV)'),
                             ('vendor_kickback_check', 'Vendor kickback check'),
                             ('other', 'Other')],
                    db_index=True, max_length=30)),
                ('payee_name', models.CharField(max_length=200)),
                ('payee_role', models.CharField(blank=True,
                                                 help_text='Title agent / lender / inspector / contractor / other',
                                                 max_length=100)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('written_disclosure_present', models.BooleanField(
                    default=False, help_text='RESPA-compliant disclosure on file?')),
                ('disclosure_url', models.CharField(blank=True, max_length=1024)),
                ('paid_at', models.DateField()),
                ('reviewed_by_attorney', models.BooleanField(default=False)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('deal', models.ForeignKey(blank=True, null=True,
                                            on_delete=django.db.models.deletion.SET_NULL,
                                            related_name='respa_payments',
                                            to='broker_ops.deal')),
            ],
            options={'ordering': ['-paid_at']},
        ),
        migrations.CreateModel(
            name='InsurancePolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('policy_type', models.CharField(
                    choices=[('eo', 'Errors & Omissions'), ('gl', 'General Liability'),
                             ('cyber', 'Cyber Liability'), ('auto', 'Commercial Auto'),
                             ('workers_comp', 'Workers Comp'), ('umbrella', 'Umbrella')],
                    db_index=True, max_length=20)),
                ('carrier', models.CharField(max_length=200)),
                ('policy_number', models.CharField(max_length=100)),
                ('coverage_limit', models.DecimalField(decimal_places=2, max_digits=12)),
                ('deductible', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('annual_premium', models.DecimalField(decimal_places=2, max_digits=10)),
                ('effective_date', models.DateField()),
                ('expiration_date', models.DateField(db_index=True)),
                ('certificate_url', models.CharField(blank=True,
                                                      help_text='Certificate of Insurance PDF',
                                                      max_length=1024)),
                ('states_covered', models.JSONField(blank=True, default=list)),
                ('notes', models.TextField(blank=True)),
                ('active', models.BooleanField(db_index=True, default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-effective_date']},
        ),
        migrations.CreateModel(
            name='GBPListing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(default='Everlight Ventures', max_length=200)),
                ('primary_market', models.CharField(default='Atlanta, GA', max_length=100)),
                ('phone', models.CharField(default='+14048004380', max_length=20)),
                ('website', models.URLField(default='https://everlightventures.io')),
                ('google_place_id', models.CharField(blank=True, max_length=200)),
                ('verified', models.BooleanField(db_index=True, default=False)),
                ('verified_at', models.DateTimeField(blank=True, null=True)),
                ('review_count', models.IntegerField(default=0)),
                ('average_rating', models.DecimalField(decimal_places=2, default=0, max_digits=3)),
                ('last_post_at', models.DateTimeField(blank=True,
                                                       help_text='Last GBP post (for SEO refresh cadence)',
                                                       null=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['-created_at']},
        ),
        migrations.CreateModel(
            name='AgentRoster',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('agent_type', models.CharField(
                    choices=[('human', 'Human team member'),
                             ('va', 'Virtual Assistant (contractor)'),
                             ('ai', 'AI agent (Hive Mind)'),
                             ('vendor', 'External vendor (CPA / attorney / title)')],
                    db_index=True, max_length=20)),
                ('role', models.CharField(help_text='e.g. Acquisitions, Disposition, Compliance', max_length=200)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('employment_start', models.DateField(blank=True, null=True)),
                ('code_of_conduct_signed', models.BooleanField(
                    default=False, help_text='For human/VA: signed code of conduct?')),
                ('code_of_conduct_signed_at', models.DateTimeField(blank=True, null=True)),
                ('background_check_complete', models.BooleanField(default=False)),
                ('mfa_enrolled', models.BooleanField(
                    default=False,
                    help_text='Django MFA TOTP device enrolled (if has admin access)?')),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-is_active', 'agent_type', 'name']},
        ),
        migrations.CreateModel(
            name='TestimonialCollection',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contact_name', models.CharField(max_length=200)),
                ('contact_role', models.CharField(
                    choices=[('seller', 'Seller'), ('buyer', 'Buyer'),
                             ('title', 'Title Co'), ('attorney', 'Attorney')],
                    max_length=50)),
                ('quote_text', models.TextField()),
                ('publication_permission', models.CharField(
                    choices=[('full_name', 'Full name + market OK'),
                             ('first_name', 'First name + market OK'),
                             ('anonymous', 'Anonymous only'),
                             ('no_publish', 'Internal use only')],
                    max_length=30)),
                ('market_city', models.CharField(blank=True, max_length=100)),
                ('deal_assignment_fee_range', models.CharField(
                    blank=True, help_text="e.g. '$5K-$10K' for FTC typicality context",
                    max_length=50)),
                ('received_at', models.DateField()),
                ('published_at', models.DateField(blank=True,
                                                    help_text='When published to landing page / GBP / etc.',
                                                    null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('deal', models.ForeignKey(blank=True, null=True,
                                            on_delete=django.db.models.deletion.SET_NULL,
                                            related_name='testimonials',
                                            to='broker_ops.deal')),
            ],
            options={'ordering': ['-received_at']},
        ),
    ]
