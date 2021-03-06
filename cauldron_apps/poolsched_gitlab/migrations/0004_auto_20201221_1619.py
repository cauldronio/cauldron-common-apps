# Generated by Django 3.1.3 on 2020-12-21 16:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('poolsched_gitlab', '0003_gl_autorefresh'),
    ]

    operations = [
        migrations.AddField(
            model_name='gltoken',
            name='instance',
            field=models.ForeignKey(default='GitLab', on_delete=django.db.models.deletion.CASCADE, to='poolsched_gitlab.glinstance', to_field='name'),
        ),
        migrations.AlterField(
            model_name='glrepo',
            name='instance',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='poolsched_gitlab.glinstance', to_field='name'),
        ),
    ]
