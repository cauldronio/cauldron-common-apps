import logging

from cauldron_apps.poolsched_autorefresh.models import IAutorefresh, IAutorefreshArchived, AutoRefreshManager
from poolsched.models import Intention

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_git'


class IGitAutoRefresh(IAutorefresh, Intention):
    objects = AutoRefreshManager()

    @property
    def backend(self):
        return 'git'

    @property
    def process_name(self):
        return 'Git Autorefresh'

    @classmethod
    def _archived_model(cls):
        return IGitAutoRefreshArchived

    class Meta:
        db_table = TABLE_PREFIX + '_autorefresh'
        verbose_name_plural = "Git Autorefresh"


class IGitAutoRefreshArchived(IAutorefreshArchived):
    objects = AutoRefreshManager()

    @property
    def process_name(self):
        return 'Git Autorefresh Archived'

    class Meta:
        db_table = TABLE_PREFIX + '_autorefresh_archived'
        verbose_name_plural = "Git Autorefresh Archived"
