from .project import Project
from .project import ProjectRole
from .repository import Repository, GitRepository, GitHubRepository, \
                        GitLabRepository, MeetupRepository

from django.db import models
from django.conf import settings


# IMPORTANT: If you are going to modify any User Reference: take a look at merge_accounts in views.py

# IMPORTANT: If you are going to change the schema, you MUST modify the schema in worker container


class AnonymousUser(models.Model):
    # When an anonymous user creates a project they are linked to a entry in this model
    # When they log in with some account this entry will be deleted so they will not be anonymous anymore
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, unique=True)


class UserWorkspace(models.Model):
    """
    This field indicates if the user has created the workspace
    in Kibana and the name
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, unique=True)
    tenant_name = models.CharField(max_length=100)
    tenant_role = models.CharField(max_length=100)
    backend_role = models.CharField(max_length=100)


class GithubUser(models.Model):
    BACKEND_NAME = 'github'
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, unique=True)
    username = models.CharField(max_length=100)
    photo = models.URLField()


class GitlabUser(models.Model):
    BACKEND_NAME = 'gitlab'
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, unique=True)
    username = models.CharField(max_length=100)
    photo = models.URLField()


class MeetupUser(models.Model):
    BACKEND_NAME = 'meetup'
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, unique=True)
    username = models.CharField(max_length=100)
    photo = models.URLField()


class SHTask(models.Model):
    # MUST BE UTC DATE
    scheduled_date = models.DateTimeField()
    started_date = models.DateTimeField(null=True)
    completed_date = models.DateTimeField(null=True)
    done = models.BooleanField(default=False)
    log_file = models.CharField(max_length=255, blank=True)
