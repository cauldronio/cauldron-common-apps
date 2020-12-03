import logging

from django.db import models
from django.conf import settings
from django.utils.timezone import now

from poolsched.models import Job


logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_gl'


class GLInstance(models.Model):
    """GLInstance of GitLab, or GitLab Enterprise"""

    name = models.CharField(max_length=40, unique=True)
    endpoint = models.CharField(max_length=200)

    class Meta:
        db_table = TABLE_PREFIX + 'instance'


class GLRepo(models.Model):
    """GitLab repository"""

    # GitLab owner
    owner = models.CharField(max_length=40)
    # GitLab repo
    repo = models.CharField(max_length=100)
    # GitLab instance
    instance = models.ForeignKey(
        GLInstance, on_delete=models.SET_NULL,
        default=None, null=True, blank=True)
    # When the repo was created in the scheduler
    created = models.DateTimeField(default=now, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'repo'
        verbose_name_plural = "Repositories GitLab"
        # The combination (owner, repo, instance) should be unique
        unique_together = ('owner', 'repo', 'instance')

    @property
    def url(self):
        return f'{self.instance.endpoint}/{self.owner}/{self.repo}'


class GLToken(models.Model):
    """GitLab token"""

    # Maximum number of jobs using a token concurrently
    MAX_JOBS_TOKEN = 3

    # GLToken string
    token = models.CharField(max_length=100)
    # Rate limit remaining, last time it was checked
    # rate = models.IntegerField(default=0)
    # Rate limit reset, last time it was checked
    reset = models.DateTimeField(default=now)
    # Owner of the token
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        default=None, null=True, blank=True,
        related_name='gltokens',
        related_query_name='gltoken')
    # Jobs using the token
    jobs = models.ManyToManyField(
        Job,
        related_name='gltokens',
        related_query_name='gltoken')

    class Meta:
        db_table = TABLE_PREFIX + 'token'
        verbose_name_plural = "Tokens GitLab"

    @property
    def is_ready(self):
        return now() > self.reset
