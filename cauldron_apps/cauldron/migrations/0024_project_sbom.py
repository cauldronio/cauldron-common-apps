# Generated by Django 3.1.3 on 2021-12-20 06:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cauldron', '0023_project_autorefresh'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='sbom',
            field=models.BooleanField(default=False),
        ),
    ]