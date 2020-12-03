import logging

from django.db import models
from django.utils.timezone import now


logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_git'


class GitRepo(models.Model):
    """Git repository"""

    url = models.CharField(max_length=255, unique=True)

    # When the repo was created in the scheduler
    created = models.DateTimeField(default=now, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'repo'
        verbose_name_plural = "Repositories Git"

