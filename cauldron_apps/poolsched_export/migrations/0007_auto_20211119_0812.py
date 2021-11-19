# Generated by Django 3.1.3 on 2021-11-19 08:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('poolsched_export', '0006_auto_20211105_0934'),
    ]

    operations = [
        migrations.RenameField(
            model_name='reportscommitsbyweek',
            old_name='location',
            new_name='location_commits'
        ),
        migrations.RemoveField(
            model_name='reportscommitsbyweek',
            name='size',
        ),
        migrations.AddField(
            model_name='reportscommitsbyweek',
            name='location_authors',
            field=models.CharField(default=None, max_length=150, null=True),
        ),
        migrations.AlterField(
            model_name='reportscommitsbyweek',
            name='location_commits',
            field=models.CharField(default=None, max_length=150, null=True),
        ),
    ]
