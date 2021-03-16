import logging

from cauldron_apps.poolsched_autorefresh.models import IAutorefresh, IAutorefreshArchived, AutoRefreshManager
from poolsched.models import Intention

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_stackexchange'


class IStackExchangeAutoRefresh(IAutorefresh, Intention):
    objects = AutoRefreshManager()

    @property
    def backend(self):
        return 'stackexchange'

    @property
    def process_name(self):
        return 'StackExchange Autorefresh'

    @classmethod
    def _archived_model(cls):
        return IStackExchangeAutoRefreshArchived

    class Meta:
        db_table = TABLE_PREFIX + '_autorefresh'
        verbose_name_plural = "StackExchange Autorefresh"


class IStackExchangeAutoRefreshArchived(IAutorefreshArchived):
    @property
    def process_name(self):
        return 'Meetup Autorefresh Archived'

    class Meta:
        db_table = TABLE_PREFIX + '_autorefresh_archived'
        verbose_name_plural = "StackExchange Autorefresh Archived"
