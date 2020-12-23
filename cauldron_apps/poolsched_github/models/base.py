import logging

from django.db import models
from django.conf import settings
from django.utils.timezone import now

from poolsched.models import Job

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_gh'


class GHInstance(models.Model):
    """GHInstance of GitHub, or GitHub Enterprise"""

    name = models.CharField(max_length=40, unique=True)
    endpoint = models.CharField(max_length=200)

    class Meta:
        db_table = TABLE_PREFIX + 'instance'


class GHRepo(models.Model):
    """GitHub repository"""

    # GitHub owner
    owner = models.CharField(max_length=40)
    # GitHub repo
    repo = models.CharField(max_length=100)
    # GitHub instance
    instance = models.ForeignKey(
        GHInstance, on_delete=models.SET_NULL,
        default=None, null=True, blank=True,
        to_field='name')
    # When the repo was created in the scheduler
    created = models.DateTimeField(default=now, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'repo'
        verbose_name_plural = "Repositories GitHub"
        # The combination (owner, repo, instance) should be unique
        unique_together = ('owner', 'repo', 'instance')

    @property
    def url(self):
        return f'{self.instance.endpoint}/{self.owner}/{self.repo}'


class GHToken(models.Model):
    """GitHub token"""

    # Maximum number of jobs using a token concurrently
    MAX_JOBS_TOKEN = 3

    # GHToken string
    token = models.CharField(max_length=40)
    # Rate limit remaining, last time it was checked
    # rate = models.IntegerField(default=0)
    # Rate limit reset, last time it was checked
    reset = models.DateTimeField(default=now)
    # Instance for the token
    instance = models.ForeignKey(GHInstance, on_delete=models.CASCADE, to_field='name', default='GitHub')
    # Owner of the token
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        default=None, null=True, blank=True,
        related_name='ghtokens',
        related_query_name='ghtoken')
    # Jobs using the token
    jobs = models.ManyToManyField(
        Job,
        related_name='ghtokens',
        related_query_name='ghtoken')
    # TODO: Include instance

    class Meta:
        db_table = TABLE_PREFIX + 'token'
        verbose_name_plural = "Tokens GitHub"

    @property
    def is_ready(self):
        return now() > self.reset

