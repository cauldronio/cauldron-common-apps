from django.db import migrations
from cauldron_apps.poolsched_gitlab.models import GLInstance


def gitlab_data(apps, schema_editor):
    GLInstance.objects.update_or_create(
        name='Gnome',
        endpoint="https://gitlab.gnome.org")


class Migration(migrations.Migration):

    dependencies = [
        ('poolsched_gitlab', '0004_auto_20201221_1619'),
    ]

    operations = [
        migrations.RunPython(gitlab_data),
    ]
