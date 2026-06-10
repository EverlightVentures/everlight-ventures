# ConsentLedger forensic anchors for TCPA legal defense (2026-04-25)
# Adds Twilio SID + verbatim reply + property lead tie-back so each consent
# row is independently subpoena-able and corroborate-able with the carrier.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('broker_ops', '0011_audit_infrastructure'),
    ]

    operations = [
        migrations.AddField(
            model_name='consentledger',
            name='outbound_twilio_sid',
            field=models.CharField(blank=True, db_index=True, max_length=64,
                                    help_text='Twilio SID of outbound disclosure SMS (subpoena anchor)'),
        ),
        migrations.AddField(
            model_name='consentledger',
            name='outbound_sent_at',
            field=models.DateTimeField(blank=True, null=True,
                                       help_text='Server-side timestamp when disclosure was sent'),
        ),
        migrations.AddField(
            model_name='consentledger',
            name='inbound_twilio_sid',
            field=models.CharField(blank=True, db_index=True, max_length=64,
                                    help_text='Twilio SID of inbound consent reply (subpoena anchor)'),
        ),
        migrations.AddField(
            model_name='consentledger',
            name='inbound_body_verbatim',
            field=models.TextField(blank=True,
                                    help_text='Exact reply body from contact -- their consent signature'),
        ),
        migrations.AddField(
            model_name='consentledger',
            name='inbound_received_at',
            field=models.DateTimeField(blank=True, null=True,
                                       help_text='Twilio server-side timestamp when reply landed'),
        ),
        migrations.AddField(
            model_name='consentledger',
            name='property_lead_id',
            field=models.CharField(blank=True, db_index=True, max_length=100,
                                    help_text='PropertyLead.id this consent belongs to (string for UUID compat)'),
        ),
        migrations.AddField(
            model_name='consentledger',
            name='evidence_payload_json',
            field=models.TextField(blank=True,
                                    help_text='Raw Twilio webhook/API payloads for outbound + inbound (audit-only)'),
        ),
        migrations.AddIndex(
            model_name='consentledger',
            index=models.Index(fields=['outbound_twilio_sid'], name='broker_ops__outbound_idx'),
        ),
        migrations.AddIndex(
            model_name='consentledger',
            index=models.Index(fields=['inbound_twilio_sid'], name='broker_ops__inbound_idx'),
        ),
        migrations.AddIndex(
            model_name='consentledger',
            index=models.Index(fields=['property_lead_id'], name='broker_ops__property_lead_idx'),
        ),
    ]
