from django.db import migrations, models


def classify_existing_tasks(apps, schema_editor):
    TaskItem = apps.get_model("taskboard", "TaskItem")
    human_categories = {"api_credential", "social_media", "email_account", "domain", "payment"}

    for task in TaskItem.objects.select_related("template").all():
        category = getattr(task.template, "category", "")
        if category in human_categories:
            task.owner_type = "human"
            task.request_kind = "input"
        else:
            task.owner_type = "ai"
            task.request_kind = "execution"
        task.save(update_fields=["owner_type", "request_kind"])


class Migration(migrations.Migration):

    dependencies = [
        ("taskboard", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="taskitem",
            name="completed_by",
            field=models.CharField(blank=True, choices=[("", "Unknown"), ("ai", "AI"), ("human", "Human"), ("system", "System")], default="", max_length=20),
        ),
        migrations.AddField(
            model_name="taskitem",
            name="owner_type",
            field=models.CharField(choices=[("ai", "AI"), ("human", "Human")], db_index=True, default="human", max_length=20),
        ),
        migrations.AddField(
            model_name="taskitem",
            name="request_kind",
            field=models.CharField(choices=[("execution", "AI Execution"), ("input", "Human Input"), ("approval", "Approval")], db_index=True, default="input", max_length=20),
        ),
        migrations.AddField(
            model_name="taskitem",
            name="result_summary",
            field=models.TextField(blank=True, help_text="Execution summary or final handoff details"),
        ),
        migrations.RunPython(classify_existing_tasks, migrations.RunPython.noop),
    ]
