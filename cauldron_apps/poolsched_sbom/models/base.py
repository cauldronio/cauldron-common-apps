import random
import string

from django.db import models
from django.conf import settings


class SPDXUserFile(models.Model):
    """Model to store the location of files uploaded by users"""

    created_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    on_delete=models.SET_NULL,
                                    null=True, blank=True,
                                    related_name='spdx_user_files',
                                    related_query_name='spdx_user_file')
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=100, unique=True)
    result = models.JSONField(null=True, default=None)

    def save(self, *args, **kwargs):
        self.location = ''.join(random.choices(string.ascii_lowercase, k=50)) + '.spdx'
        super().save(*args, **kwargs)
