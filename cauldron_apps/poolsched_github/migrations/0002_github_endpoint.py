from django.db import migrations
from cauldron_apps.poolsched_github.models import GHInstance


def github_data(apps, schema_editor):
    """Add data for GitHub"""
    GHInstance.objects.update_or_create(
        name='GitHub',
        endpoint="https://github.com")


class Migration(migrations.Migration):

    dependencies = [
        ('poolsched_github', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(github_data),
    ]
