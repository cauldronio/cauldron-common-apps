# Generated by Django 3.1.3 on 2021-04-30 10:30

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cauldron', '0016_auto_20210427_1020'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='fork_from',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='cauldron.project'),
        ),
    ]
