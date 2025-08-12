from django.db import migrations, models
from django.conf import settings


def backfill_owner(apps, schema_editor):
    ContextEntry = apps.get_model('contexts', 'ContextEntry')
    User = apps.get_model('auth', 'User')
    user = User.objects.order_by('id').first()
    if not user:
        return
    ContextEntry.objects.filter(owner__isnull=True).update(owner=user)


class Migration(migrations.Migration):
    dependencies = [
        ('contexts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='contextentry',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=models.deletion.CASCADE, related_name='contexts', to=settings.AUTH_USER_MODEL),
        ),
        migrations.RunPython(backfill_owner, migrations.RunPython.noop),
    ]


