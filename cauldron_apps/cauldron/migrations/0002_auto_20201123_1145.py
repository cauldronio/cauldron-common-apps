# Generated by Django 3.1.3 on 2020-11-23 11:45

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('cauldron', '0001_initial'),
        ('poolsched_github', '0001_initial'),
        ('poolsched_gitlab', '0001_initial'),
        ('poolsched_git', '0001_initial'),
        ('poolsched_meetup', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='meetuprepository',
            name='repo_sched',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to='poolsched_meetup.meetuprepo'),
        ),
        migrations.AddField(
            model_name='gitrepository',
            name='repo_sched',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to='poolsched_git.gitrepo'),
        ),
        migrations.AddField(
            model_name='gitlabrepository',
            name='repo_sched',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to='poolsched_gitlab.glrepo'),
        ),
        migrations.AddField(
            model_name='githubrepository',
            name='repo_sched',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.SET_NULL, to='poolsched_github.ghrepo'),
        ),
        migrations.AlterUniqueTogether(
            name='gitlabrepository',
            unique_together={('owner', 'repo')},
        ),
        migrations.AlterUniqueTogether(
            name='githubrepository',
            unique_together={('owner', 'repo')},
        ),
    ]
