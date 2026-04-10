# Generated manually 2026-04-09
# Adds: DealEvent, CallLog models + new Deal stage choices

import django.db.models.deletion
import django.utils.timezone
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("broker_ops", "0005_alter_offerlisting_seller_email_clientfile_and_more"),
    ]

    operations = [
        # Update Deal.stage choices (just needs field alteration)
        migrations.AlterField(
            model_name="deal",
            name="stage",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("intro", "Intro Made"),
                    ("negotiating", "Negotiating"),
                    ("contracted", "Contracted"),
                    ("legal_review", "Legal Review (Justine)"),
                    ("signing", "Awaiting Signatures"),
                    ("title_engaged", "Title Company Engaged"),
                    ("closing", "Closing in Progress"),
                    ("active", "Active / In Progress"),
                    ("closed_won", "Closed Won"),
                    ("closed_lost", "Closed Lost"),
                ],
                default="intro",
            ),
        ),

        # DealEvent model
        migrations.CreateModel(
            name="DealEvent",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("event_type", models.CharField(
                    max_length=30, db_index=True,
                    choices=[
                        ("stage_change", "Stage Change"),
                        ("contract_generated", "Contract Generated"),
                        ("legal_review", "Legal Review"),
                        ("legal_approved", "Legal Approved"),
                        ("legal_flagged", "Legal Issue Flagged"),
                        ("doc_sent", "Document Sent"),
                        ("doc_signed", "Document Signed"),
                        ("title_engaged", "Title Company Engaged"),
                        ("emd_deposited", "EMD Deposited"),
                        ("emd_released", "EMD Released"),
                        ("invoice_created", "Invoice Created"),
                        ("invoice_paid", "Invoice Paid"),
                        ("call_logged", "Call Logged"),
                        ("email_sent", "Email Sent"),
                        ("email_received", "Email Received"),
                        ("note", "Internal Note"),
                        ("closing_scheduled", "Closing Scheduled"),
                        ("funds_disbursed", "Funds Disbursed"),
                    ],
                )),
                ("title", models.CharField(max_length=300)),
                ("detail", models.TextField(blank=True)),
                ("agent_name", models.CharField(blank=True, max_length=50, help_text="Hive agent who performed action")),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("deal", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="events",
                    to="broker_ops.deal",
                )),
            ],
            options={
                "ordering": ["-created_at"],
                "verbose_name": "Deal Event",
            },
        ),

        # CallLog model
        migrations.CreateModel(
            name="CallLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("call_type", models.CharField(max_length=20, choices=[
                    ("seller_intro", "Seller Introduction"),
                    ("seller_followup", "Seller Follow-up"),
                    ("negotiation", "Negotiation Call"),
                    ("buyer_pitch", "Buyer Pitch"),
                    ("buyer_followup", "Buyer Follow-up"),
                    ("title_company", "Title Company"),
                    ("legal_review", "Legal / Compliance"),
                    ("closing_call", "Closing Coordination"),
                    ("other", "Other"),
                ])),
                ("outcome", models.CharField(blank=True, max_length=20, choices=[
                    ("connected", "Connected - Positive"),
                    ("connected_neg", "Connected - Negative / Not Interested"),
                    ("voicemail", "Left Voicemail"),
                    ("no_answer", "No Answer"),
                    ("callback", "Callback Scheduled"),
                    ("deal_advanced", "Deal Advanced to Next Stage"),
                    ("dead", "Lead Dead"),
                ])),
                ("direction", models.CharField(max_length=10, default="outbound", choices=[
                    ("outbound", "Outbound"),
                    ("inbound", "Inbound"),
                ])),
                ("caller_agent", models.CharField(max_length=50, help_text="Hive agent: piper, hammer, harrison")),
                ("contact_name", models.CharField(blank=True, max_length=200)),
                ("contact_phone", models.CharField(blank=True, max_length=20)),
                ("contact_email", models.EmailField(blank=True, max_length=254)),
                ("started_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("duration_secs", models.IntegerField(default=0)),
                ("notes", models.TextField(blank=True, help_text="Free-form notes during call")),
                ("seller_mood", models.CharField(blank=True, max_length=20, choices=[
                    ("motivated", "Motivated"),
                    ("neutral", "Neutral"),
                    ("resistant", "Resistant"),
                    ("hostile", "Hostile"),
                ])),
                ("price_discussed", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True,
                                                         help_text="Price mentioned on call")),
                ("objections", models.JSONField(blank=True, default=list, help_text="List of objections raised")),
                ("commitments", models.JSONField(blank=True, default=list, help_text="List of commitments/next steps agreed")),
                ("followup_date", models.DateTimeField(blank=True, null=True)),
                ("followup_action", models.CharField(blank=True, max_length=300)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("deal", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="calls",
                    to="broker_ops.deal",
                )),
                ("property_lead", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="calls",
                    to="broker_ops.propertylead",
                )),
                ("investor_buyer", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="calls",
                    to="broker_ops.investorbuyer",
                )),
            ],
            options={
                "ordering": ["-started_at"],
                "verbose_name": "Call Log",
            },
        ),
    ]
