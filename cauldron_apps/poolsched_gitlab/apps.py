from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate
import logging


Logger = logging.getLogger(__name__)


def load_gitlab_instances(app_config, **kwargs):
    GLInstance = app_config.get_model('GLInstance')
    base_id = 'GL_CLIENT_ID_'
    base_secret = 'GL_CLIENT_SECRET_'
    gitlab_instances = [
        ("GitLab", "https://gitlab.com"),
        ("Gnome", "https://gitlab.gnome.org"),
        ("KDE", "https://invent.kde.org"),
    ]

    for instance in gitlab_instances:
        name = instance[0]
        endpoint = instance[1]

        obj, _ = GLInstance.objects.get_or_create(name=name,
                                                  defaults={'endpoint': endpoint,
                                                            'slug': f'{name.lower()}'})

        try:
            obj.client_id = getattr(settings, f'{base_id}{name.upper()}')
            obj.client_secret = getattr(settings, f'{base_secret}{name.upper()}')
            obj.save()

            Logger.info(f"{name} instance loaded.")
        except AttributeError:
            Logger.error(f"{name} instance not set.")


class CauldronGitlabConfig(AppConfig):
    name = 'cauldron_apps.poolsched_gitlab'

    def ready(self):
        # Load after the migration is done
        post_migrate.connect(load_gitlab_instances, sender=self)
