from .project import Project
from .project import ProjectRole
from .repository import Repository, GitRepository, GitHubRepository, \
                        GitLabRepository, MeetupRepository, StackExchangeRepository
from .results import RepositoryMetrics
from .ighowner import IAddGHOwner, IAddGHOwnerArchived
from .iglowner import IAddGLOwner, IAddGLOwnerArchived

from django.db import models
from django.conf import settings


# IMPORTANT: If you are going to modify any User Reference: take a look at merge_accounts in views.py

# IMPORTANT: If you are going to change the schema, you MUST modify the schema in worker container


class AnonymousUser(models.Model):
    # When an anonymous user creates a project they are linked to a entry in this model
    # When they log in with some account this entry will be deleted so they will not be anonymous anymore
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, unique=True)


class AuthorizedBackendUser(models.Model):
    """
    Identify if a user has permissions to access Cauldron.
    Admin users are not necessarily to be in this model.
    """
    backend = models.CharField(max_length=20)
    username = models.CharField(max_length=100)

    class Meta:
        unique_together = ('username', 'backend')


class UserWorkspace(models.Model):
    """
    This field indicates if the user has created the workspace
    in Kibana and the name
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, unique=True)
    tenant_name = models.CharField(max_length=100)
    tenant_role = models.CharField(max_length=100)
    backend_role = models.CharField(max_length=100)


class OauthUser(models.Model):
    backend = models.CharField(max_length=20)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    username = models.CharField(max_length=100)
    photo = models.URLField(null=True)

    class Meta:
        unique_together = ("username", "backend")


class BannerMessage(models.Model):
    """
    Messages to show to authenticated users and keep a register
    to know if they read/ignored it
    """
    message = models.TextField()
    created = models.DateTimeField(auto_created=True)
    read_by = models.ManyToManyField(to=settings.AUTH_USER_MODEL, blank=True)
    color = models.TextField(default="alert-info")
    border_color = models.TextField(default="border-left-primary")
    text_color = models.TextField(default="text-dark")
