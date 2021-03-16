import logging

from django.db import models
from django.conf import settings
from django.utils.timezone import now

from poolsched.models import Job

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_stackexchange'


class StackExchangeQuestionTag(models.Model):
    """StackExchange Question tag"""
    # site must be the full domain name, eg. 'stackoverflow.com'
    site = models.CharField(max_length=100)
    tagged = models.CharField(max_length=100)
    created = models.DateTimeField(default=now, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'qtag'
        verbose_name_plural = "StackExchange question tag"
        unique_together = ['site', 'tagged']

    @property
    def url(self):
        return f'https://{self.site}/questions/tagged/{self.tagged}'


class StackExchangeToken(models.Model):
    MAX_JOBS_TOKEN = 3

    # StackExchange token
    token = models.CharField(max_length=40)
    api_key = models.CharField(max_length=40)
    # Rate limit reset, last time it was checked
    reset = models.DateTimeField(default=now)
    # Owner of the token
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        default=None, null=True, blank=True,
        related_name='stackexchangetokens',
        related_query_name='stackexchangetoken')
    # Jobs using the token
    jobs = models.ManyToManyField(
        Job,
        related_name='stackexchangetokens',
        related_query_name='stackexchangetoken')

    class Meta:
        db_table = TABLE_PREFIX + 'token'
        verbose_name_plural = "Tokens StackExchange"

    @property
    def is_ready(self):
        return now() > self.reset
