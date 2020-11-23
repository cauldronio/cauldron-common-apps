from django.db import migrations
from cauldron_apps.poolsched_gitlab.models import GLInstance


def gitlab_data(apps, schema_editor):
    GLInstance.objects.update_or_create(
        name='GitLab',
        endpoint="https://gitlab.com")


class Migration(migrations.Migration):

    dependencies = [
        ('poolsched_gitlab', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(gitlab_data),
    ]
