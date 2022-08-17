import datetime
import logging
from urllib.parse import urljoin

import requests
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
    slug = models.CharField(max_length=40)
    client_id = models.CharField(max_length=64, null=True, default=None)
    client_secret = models.CharField(max_length=64, null=True, default=None)

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
        default=None, null=True, blank=True,
        to_field='name')
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
    # Instance for the token
    instance = models.ForeignKey(GLInstance, on_delete=models.CASCADE, to_field='name', default='GitLab')
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
    # Define whether the token can expire
    expiring_token = models.BooleanField(default=True)
    # Token used for refreshing the token when expired
    refresh_token = models.CharField(max_length=100, null=True, default=None)
    # Date at which the token is expired
    expiration_date = models.DateTimeField(null=True, default=None)

    class Meta:
        db_table = TABLE_PREFIX + 'token'
        verbose_name_plural = "Tokens GitLab"

    @property
    def is_ready(self):
        return now() > self.reset

    def update_token(self):
        payload = {'refresh_token': self.refresh_token,
                   'grant_type': 'refresh_token',
                   'client_id': self.instance.client_id,
                   'client_secret': self.instance.client_secret}
        r = requests.post(urljoin(self.instance.endpoint, '/oauth/token'),
                          params=payload)
        if r.ok:
            data = r.json()
            self.refresh_token = data['refresh_token']
            self.token = data['access_token']
            self.expiration_date = now() + datetime.timedelta(seconds=7200)
            self.save()
        return r.ok
