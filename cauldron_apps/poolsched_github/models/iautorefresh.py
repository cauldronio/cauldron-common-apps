import logging
from poolsched.models import Intention
from cauldron_apps.poolsched_autorefresh.models import IAutorefresh, IAutorefreshArchived, AutoRefreshManager


logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_gh'


class IGHIssueAutoRefresh(IAutorefresh, Intention):
    objects = AutoRefreshManager()

    @property
    def backend(self):
        return 'github:issue'

    @property
    def process_name(self):
        return 'GH Issue Autorefresh'

    @classmethod
    def _archived_model(cls):
        return IGHIssueAutoRefreshArchived

    class Meta:
        db_table = TABLE_PREFIX + '_issue_autorefresh'
        verbose_name_plural = "GH Issue Autorefresh"


class IGHIssueAutoRefreshArchived(IAutorefreshArchived):
    @property
    def process_name(self):
        return 'GH Issue Autorefresh Archived'

    class Meta:
        db_table = TABLE_PREFIX + '_issue_autorefresh_archived'
        verbose_name_plural = "GH Issue Autorefresh Archived"


class IGHRepoAutoRefresh(IAutorefresh, Intention):
    objects = AutoRefreshManager()

    @property
    def backend(self):
        return 'github:repo'

    @property
    def process_name(self):
        return 'GH Repo Autorefresh'

    @classmethod
    def _archived_model(cls):
        return IGHRepoAutoRefreshArchived

    class Meta:
        db_table = TABLE_PREFIX + '_repo_autorefresh'
        verbose_name_plural = "GH Repo Autorefresh"


class IGHRepoAutoRefreshArchived(IAutorefreshArchived):
    @property
    def process_name(self):
        return 'GH Repo Autorefresh Archived'

    class Meta:
        db_table = TABLE_PREFIX + '_repo_autorefresh_archived'
        verbose_name_plural = "GH Repo Autorefresh Archived"


class IGH2IssueAutoRefresh(IAutorefresh, Intention):
    objects = AutoRefreshManager()

    @property
    def backend(self):
        return 'github2:issue'

    @property
    def process_name(self):
        return 'GH2 Issue Autorefresh'

    @classmethod
    def _archived_model(cls):
        return IGH2IssueAutoRefreshArchived

    class Meta:
        db_table = TABLE_PREFIX + '2_issue_autorefresh'
        verbose_name_plural = "GH2 Issue Autorefresh"


class IGH2IssueAutoRefreshArchived(IAutorefreshArchived):
    @property
    def process_name(self):
        return 'GH2 Issue Autorefresh Archived'

    class Meta:
        db_table = TABLE_PREFIX + '2_issue_autorefresh_archived'
        verbose_name_plural = "GH2 Issue Autorefresh Archived"
