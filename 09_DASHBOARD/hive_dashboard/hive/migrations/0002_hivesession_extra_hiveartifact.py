# Generated for hive_logger integration
# Adds canonical logging fields to HiveSession and the HiveArtifact table.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('hive', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='hivesession',
            name='agent',
            field=models.CharField(blank=True, db_index=True, max_length=64),
        ),
        migrations.AddField(
            model_name='hivesession',
            name='task',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='hivesession',
            name='artifacts_count',
            field=models.IntegerField(default=0),
        ),
        migrations.CreateModel(
            name='HiveArtifact',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('agent', models.CharField(db_index=True, max_length=64)),
                ('kind', models.CharField(choices=[
                    ('gdoc', 'Google Doc'),
                    ('html', 'HTML Report'),
                    ('file', 'File'),
                    ('slack_post', 'Slack Post'),
                    ('blinko_note', 'Blinko Note'),
                    ('supabase_row', 'Supabase Row'),
                ], db_index=True, max_length=32)),
                ('title', models.CharField(blank=True, max_length=255)),
                ('url', models.CharField(blank=True, max_length=1024)),
                ('path', models.CharField(blank=True, max_length=1024)),
                ('tags', models.JSONField(blank=True, default=list)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('session', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='artifacts',
                    to='hive.hivesession',
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='hiveartifact',
            index=models.Index(fields=['kind', '-created_at'], name='hive_hiveart_kind_idx'),
        ),
        migrations.AddIndex(
            model_name='hiveartifact',
            index=models.Index(fields=['agent', '-created_at'], name='hive_hiveart_agent_idx'),
        ),
    ]
