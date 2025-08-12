from django.db import migrations, models
from django.conf import settings


def backfill_owner(apps, schema_editor):
    Task = apps.get_model('tasks', 'Task')
    User = apps.get_model('auth', 'User')
    user = User.objects.order_by('id').first()
    if user:
        # Best effort: set owner on legacy rows
        Task.objects.filter(owner__isnull=True).update(owner_id=user.id)


class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0001_initial'),
    ]

    operations = [
        # Only adjust STATE; the column already exists in the live DB.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AddField(
                    model_name='task',
                    name='owner',
                    field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, related_name='tasks', to=settings.AUTH_USER_MODEL),
                )
            ],
        ),
        migrations.RunPython(backfill_owner, migrations.RunPython.noop),
    ]


