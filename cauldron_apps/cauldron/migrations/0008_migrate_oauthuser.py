# Generated by Django 3.1.3 on 2021-01-14 08:04

from django.db import migrations


def migrate_oauth_models(apps, schema_editor):
    OauthUser = apps.get_model('cauldron', 'OauthUser')
    GithubUser = apps.get_model('cauldron', 'GithubUser')
    GitlabUser = apps.get_model('cauldron', 'GitlabUser')
    MeetupUser = apps.get_model('cauldron', 'MeetupUser')
    GnomeUser = apps.get_model('cauldron', 'GnomeUser')
    objs = []
    for row in GithubUser.objects.all():
        obj = OauthUser(backend='github', user=row.user, username=row.username, photo=row.photo)
        objs.append(obj)
    for row in GitlabUser.objects.all():
        obj = OauthUser(backend='gitlab', user=row.user, username=row.username, photo=row.photo)
        objs.append(obj)
    for row in MeetupUser.objects.all():
        obj = OauthUser(backend='meetup', user=row.user, username=row.username, photo=row.photo)
        objs.append(obj)
    for row in GnomeUser.objects.all():
        obj = OauthUser(backend='gnome', user=row.user, username=row.username, photo=row.photo)
        objs.append(obj)
    OauthUser.objects.bulk_create(objs, batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('cauldron', '0007_oauthuser'),
    ]

    operations = [
        migrations.RunPython(migrate_oauth_models)
    ]
