import logging

from poolsched.models import Intention
from cauldron_apps.poolsched_autorefresh.models import IAutorefresh, IAutorefreshArchived, AutoRefreshManager


logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_gl'


class IGLIssueAutoRefresh(IAutorefresh, Intention):
    objects = AutoRefreshManager()

    @property
    def backend(self):
        return 'gitlab:issue'

    @property
    def process_name(self):
        return 'GL Issue Autorefresh'

    @classmethod
    def _archived_model(cls):
        return IGLIssueAutoRefreshArchived

    class Meta:
        db_table = TABLE_PREFIX + '_issue_autorefresh'
        verbose_name_plural = "GL Issue Autorefresh"


class IGLIssueAutoRefreshArchived(IAutorefreshArchived):
    @property
    def process_name(self):
        return 'GL Issue Autorefresh Archived'

    class Meta:
        db_table = TABLE_PREFIX + '_issue_autorefresh_archived'
        verbose_name_plural = "GL Issue Autorefresh Archived"


class IGLMergeAutoRefresh(IAutorefresh, Intention):
    objects = AutoRefreshManager()

    @property
    def backend(self):
        return 'gitlab:merge'

    @property
    def process_name(self):
        return 'GL Merge Autorefresh'

    @classmethod
    def _archived_model(cls):
        return IGLMergeAutoRefreshArchived

    class Meta:
        db_table = TABLE_PREFIX + '_merge_autorefresh'
        verbose_name_plural = "GL Merge Autorefresh"


class IGLMergeAutoRefreshArchived(IAutorefreshArchived):
    @property
    def process_name(self):
        return 'GL Merge Autorefresh Archived'

    class Meta:
        db_table = TABLE_PREFIX + '_merge_autorefresh_archived'
        verbose_name_plural = "GL Merge Autorefresh Archived"
