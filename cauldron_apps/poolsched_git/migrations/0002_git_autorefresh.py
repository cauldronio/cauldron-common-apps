# Generated by Django 3.1.3 on 2020-12-01 16:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('poolsched', '0001_initial'),
        ('poolsched_git', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='IGitAutoRefresh',
            fields=[
                ('intention_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='poolsched.intention')),
                ('last_autorefresh', models.DateTimeField(null=True)),
                ('scheduled', models.DateTimeField()),
            ],
            options={
                'verbose_name_plural': 'Git Autorefresh',
                'db_table': 'poolsched_git_autorefresh',
            },
            bases=('poolsched.intention',),
        ),
        migrations.CreateModel(
            name='IGitAutoRefreshArchived',
            fields=[
                ('archivedintention_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='poolsched.archivedintention')),
                ('last_autorefresh', models.DateTimeField(null=True)),
                ('scheduled', models.DateTimeField()),
            ],
            options={
                'verbose_name_plural': 'Git Autorefresh Archived',
                'db_table': 'poolsched_git_autorefresh_archived',
            },
            bases=('poolsched.archivedintention',),
        ),
    ]