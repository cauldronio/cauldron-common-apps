import logging
import os

from django.conf import settings

try:
    from sirmordred.config import Config
except ImportError:
    from . import sirmordred_fake
    Config = sirmordred_fake.Config

logger = logging.getLogger("mordred-worker")

ELASTIC_URL = 'https://admin:{}@{}:{}'.format(settings.ES_ADMIN_PASSWORD,
                                              settings.ES_IN_HOST,
                                              settings.ES_IN_PORT)
MORDRED_UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
ALIASES_FILE = os.path.join(MORDRED_UTILS_DIR, 'aliases.json')
if settings.SORTINGHAT:
    MORDRED_FILE = os.path.join(MORDRED_UTILS_DIR, 'setup-sortinghat.cfg')
else:
    MORDRED_FILE = os.path.join(MORDRED_UTILS_DIR, 'setup.cfg')


class Backend:
    def __init__(self):
        self.config = Config(MORDRED_FILE)
        self.config.set_param('es_collection', 'url', ELASTIC_URL)
        self.config.set_param('es_enrichment', 'url', ELASTIC_URL)
        self.config.set_param('general', 'aliases_file', ALIASES_FILE)
        if settings.SORTINGHAT:
            self.config.set_param('sortinghat', 'host', settings.SORTINGHAT_HOST)
            self.config.set_param('sortinghat', 'database', settings.SORTINGHAT_DATABASE)
            self.config.set_param('sortinghat', 'user', settings.SORTINGHAT_USER)
            self.config.set_param('sortinghat', 'password', settings.SORTINGHAT_PASSWORD)

    def start_analysis(self):
        """Call to Grimoirelab"""

    def run(self):
        raise NotImplementedError
