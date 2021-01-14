from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate
import logging


Logger = logging.getLogger(__name__)


def load_gitlab_keys(app_config, **kwargs):
    GLInstance = app_config.get_model('GLInstance')
    base_id = 'GL_CLIENT_ID_'
    base_secret = 'GL_CLIENT_SECRET_'
    for instance in GLInstance.objects.all():
        try:
            name = instance.name.upper()
            instance.client_id = getattr(settings, f'{base_id}{name}')
            instance.client_secret = getattr(settings, f'{base_secret}{name}')
            instance.save()
            Logger.info(f"Oauth key for {instance.name} loaded.")
        except AttributeError:
            if not instance.client_id or not instance.client_secret:
                Logger.error(f"Oauth key for {instance.name} not set.")


class CauldronGitlabConfig(AppConfig):
    name = 'cauldron_apps.poolsched_gitlab'

    def ready(self):
        # Load after the migration is done
        post_migrate.connect(load_gitlab_keys, sender=self)
