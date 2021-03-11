# Generated by Django 3.1.3 on 2021-03-10 09:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('cauldron', '0011_authorizedbackenduser'),
        ('poolsched', '0001_initial'),
        ('cauldron_actions', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='IRefreshActionsArchived',
            fields=[
                ('archivedintention_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='poolsched.archivedintention')),
                ('project', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='cauldron.project')),
            ],
            options={
                'verbose_name_plural': 'RefreshActions Intentions Archived',
                'db_table': 'poolsched_IRefreshActions_archived',
            },
            bases=('poolsched.archivedintention',),
        ),
        migrations.CreateModel(
            name='IRefreshActions',
            fields=[
                ('intention_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='poolsched.intention')),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='cauldron.project')),
            ],
            options={
                'verbose_name_plural': 'Refresh Actions Intentions',
                'db_table': 'poolsched_IRefreshActions',
            },
            bases=('poolsched.intention',),
        ),
    ]
