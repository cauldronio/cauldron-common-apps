import os
from datetime import datetime, timedelta

import pytz
from django.apps import apps
from django.db import models
from django.conf import settings
from django.db.models import Q

from .repository import GitHubRepository, GitLabRepository, MeetupRepository, GitRepository, StackExchangeRepository
from .backends import Backends
from ..opendistro import OpendistroApi, BACKEND_INDICES

ELASTIC_URL = 'https://admin:{}@{}:{}'.format(settings.ES_ADMIN_PASSWORD,
                                              settings.ES_IN_HOST,
                                              settings.ES_IN_PORT)

PATH_STATIC_FILES = '/download/'


class Project(models.Model):
    name = models.CharField(max_length=32, blank=False, default=None)
    created = models.DateTimeField(auto_now_add=True)
    public = models.BooleanField(default=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.SET_NULL,
                                blank=True,
                                null=True)
    fork_from = models.ForeignKey('self',
                                  on_delete=models.SET_NULL,
                                  blank=True,
                                  null=True,
                                  default=None)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'creator'], name='unique_project_name_user')
        ]

    def __str__(self):
        return f"{self.pk} - {self.name}"

    @property
    def is_outdated(self):
        limit = datetime.now(pytz.utc) - timedelta(days=7)
        for repo in self.repository_set.select_subclasses():
            if not repo.last_refresh or repo.last_refresh < limit:
                return True
        return False

    @property
    def last_refresh(self):
        """
        Return the oldest repository update.
        If a repository has not been analyzed, return None
        """
        repo = self.repository_set.earliest('last_refresh')
        return repo.last_refresh

    def export_summary(self):
        data = {
            'csv': {},
            'kbn_reports': {}
        }
        for backend_id, backend_name in Backends.choices:
            name = str(backend_name).upper()
            if backend_id == Backends.UNKNOWN:
                continue
            try:
                file = self.file_exported.filter(backend=backend_id).latest('created')
            except models.ObjectDoesNotExist:
                file = None
            running = self.iexport_csv.filter(backend=backend_id).exists()
            if file:
                data['csv'][name] = {
                    'created': file.created,
                    'link': os.path.join(PATH_STATIC_FILES, file.location),
                    'size': file.size,
                    'running': running
                }
            elif running:
                data['csv'][name] = {'running': running}
        for kbn_report in self.kbn_report.order_by('-created')[:8].values('id', 'location', 'progress'):
            data['kbn_reports'][str(kbn_report['id'])] = kbn_report
        return data

    def summary(self):
        """Get a summary about the repositories in the project"""
        total = self.repository_set.count()
        n_git = GitRepository.objects.filter(projects=self).count()
        n_github = GitHubRepository.objects.filter(projects=self).count()
        n_gitlab = GitLabRepository.objects.filter(projects=self, instance='GitLab').count()
        n_gnome = GitLabRepository.objects.filter(projects=self, instance='Gnome').count()
        n_kde = GitLabRepository.objects.filter(projects=self, instance='KDE').count()
        n_meetup = MeetupRepository.objects.filter(projects=self).count()
        n_stack_exchange = StackExchangeRepository.objects.filter(projects=self).count()
        running = self.repos_running()

        IRefreshActions = apps.get_model('cauldron_actions.IRefreshActions')
        refresh_actions = IRefreshActions.objects.filter(project=self).exists()

        summary = {
            'id': self.id,
            'total': total,
            'running': running,
            'git': n_git,
            'github': n_github,
            'gitlab': n_gitlab,
            'gnome': n_gnome,
            'kde': n_kde,
            'meetup': n_meetup,
            'stackexchange': n_stack_exchange,
            'refresh_actions': refresh_actions
        }
        return summary

    def url_list(self):
        """Returns a list with the URLs of the repositories within the project"""
        urls = []
        for repo in self.repository_set.select_subclasses():
            urls.append(repo.datasource_url)
        return urls

    def repos_running(self):
        git = GitRepository.objects.filter(projects=self).filter(repo_sched__isnull=False)
        git_running = git.filter(Q(repo_sched__igitraw__isnull=False) | Q(repo_sched__igitenrich__isnull=False))\
            .count()
        gh = GitHubRepository.objects.filter(projects=self).filter(repo_sched__isnull=False)
        gh_running = gh.filter(Q(repo_sched__ighraw__isnull=False) | Q(repo_sched__ighenrich__isnull=False))\
            .count()
        gl = GitLabRepository.objects.filter(projects=self).filter(repo_sched__isnull=False)
        gl_running = gl.filter(Q(repo_sched__iglraw__isnull=False) | Q(repo_sched__iglenrich__isnull=False))\
            .count()
        meetup = MeetupRepository.objects.filter(projects=self).filter(repo_sched__isnull=False)
        meetup_running = meetup.filter(Q(repo_sched__imeetupraw__isnull=False) | Q(repo_sched__imeetupenrich__isnull=False))\
            .count()
        stack = StackExchangeRepository.objects.filter(projects=self).filter(repo_sched__isnull=False)
        stack_running = stack.filter(Q(repo_sched__istackexchangeraw__isnull=False) | Q(repo_sched__istackexchangeenrich__isnull=False))\
            .count()
        return git_running + gh_running + gl_running + meetup_running + stack_running

    def create_es_role(self):
        if hasattr(self, 'projectrole'):
            return
        role = f"role_project_{self.id}"
        backend_role = f"br_project_{self.id}"

        od_api = OpendistroApi(ELASTIC_URL, settings.ES_ADMIN_PASSWORD)
        od_api.create_role(role)
        od_api.create_mapping(role, backend_roles=[backend_role])

        ProjectRole.objects.create(role=role, backend_role=backend_role, project=self)

    def update_elastic_role(self):
        odfe_api = OpendistroApi(ELASTIC_URL, settings.ES_ADMIN_PASSWORD)
        permissions = []
        for index in BACKEND_INDICES['git']:
            url_list = [repo.datasource_url for repo in GitRepository.objects.filter(projects=self)]
            index_permissions = OpendistroApi.create_index_permissions(url_list, index)
            permissions.append(index_permissions)
        for index in BACKEND_INDICES['github']:
            url_list = [repo.datasource_url for repo in GitHubRepository.objects.filter(projects=self)]
            index_permissions = OpendistroApi.create_index_permissions(url_list, index)
            permissions.append(index_permissions)
        for index in BACKEND_INDICES['gitlab']:
            url_list = [repo.datasource_url for repo in GitLabRepository.objects.filter(projects=self)]
            index_permissions = OpendistroApi.create_index_permissions(url_list, index)
            permissions.append(index_permissions)
        for index in BACKEND_INDICES['meetup']:
            url_list = [repo.datasource_url for repo in MeetupRepository.objects.filter(projects=self)]
            index_permissions = OpendistroApi.create_index_permissions(url_list, index)
            permissions.append(index_permissions)
        for index in BACKEND_INDICES['stackexchange']:
            url_list = [repo.datasource_url for repo in StackExchangeRepository.objects.filter(projects=self)]
            index_permissions = OpendistroApi.create_index_permissions(url_list, index)
            permissions.append(index_permissions)
        odfe_api.update_elastic_role(self.projectrole.role, permissions)

    def fork(self, creator):
        name, num = self.name, 2
        while creator.project_set.filter(name=name).exists():
            name = f'{self.name[:25]} ({num})'
            num += 1

        report = self.__class__.objects.create(
            name=name,
            creator=creator,
            fork_from=self)
        report.create_es_role()
        report.repository_set.set(self.repository_set.all())
        report.update_elastic_role()
        for action in self.action_set.order_by('created').select_subclasses():
            action.id = None
            action.pk = None
            action._state.adding = True
            action.creator = creator
            action.project = report
            action.save()
        return report


class ProjectRole(models.Model):
    role = models.CharField(max_length=255, unique=True)
    backend_role = models.CharField(max_length=255, unique=True)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, unique=True)

    def __str__(self):
        return f"{self.pk} - {self.role}, {self.project}"
