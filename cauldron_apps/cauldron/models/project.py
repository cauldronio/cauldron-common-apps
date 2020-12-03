from datetime import datetime, timedelta

import pytz
from django.db import models
from django.conf import settings
from django.db.models import Q

from .repository import GitHubRepository, GitLabRepository, MeetupRepository, GitRepository
from ..opendistro import OpendistroApi, BACKEND_INDICES

ELASTIC_URL = 'https://admin:{}@{}:{}'.format(settings.ES_ADMIN_PASSWORD,
                                              settings.ES_IN_HOST,
                                              settings.ES_IN_PORT)



class Project(models.Model):
    name = models.CharField(max_length=32, blank=False, default=None)
    created = models.DateTimeField(auto_now_add=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.SET_NULL,
                                blank=True,
                                null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['name', 'creator'], name='unique_project_name_user')
        ]

    def __str__(self):
        return f"{self.pk} - {self.name}"

    @property
    def is_outdated(self):
        limit = datetime.now(pytz.utc) - timedelta(days=5)
        for repo in self.repository_set.select_subclasses():
            if not repo.last_refresh or repo.last_refresh < limit:
                return True
        return False

    @property
    def last_refresh(self):
        last_refresh = None
        for repo in self.repository_set.select_subclasses():
            if not repo.last_refresh:
                continue
            if not last_refresh:
                last_refresh = repo.last_refresh
                continue
            if repo.last_refresh < last_refresh:
                last_refresh = repo.last_refresh
        return last_refresh

    def summary(self):
        """Get a summary about the repositories in the project"""
        total = self.repository_set.count()
        n_git = GitRepository.objects.filter(projects=self).count()
        n_github = GitHubRepository.objects.filter(projects=self).count()
        n_gitlab = GitLabRepository.objects.filter(projects=self).count()
        n_meetup = MeetupRepository.objects.filter(projects=self).count()
        running = self.repos_running()
        summary = {
            'id': self.id,
            'total': total,
            'running': running,
            'git': n_git,
            'github': n_github,
            'gitlab': n_gitlab,
            'meetup': n_meetup
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
        return git_running + gh_running + gl_running + meetup_running

    def repos_status(self):
        git = GitRepository.objects.filter(projects=self).filter(repo_sched__isnull=False)
        git_running = git.filter(Q(repo_sched__igitraw__isnull=False) | Q(repo_sched__igitenrich__isnull=False))
        git_finish = git.filter(Q(repo_sched__igitraw__isnull=True) | Q(repo_sched__igitenrich__isnull=True))\
            .filter(Q(repo_sched__igitenricharchived__isnull=False) | Q(repo_sched__igitrawarchived__isnull=False))
        gh = GitHubRepository.objects.filter(projects=self).filter(repo_sched__isnull=False)
        gh_running = gh.filter(Q(repo_sched__ighraw__isnull=False) | Q(repo_sched__ighenrich__isnull=False))
        gh_finish = gh.filter(Q(repo_sched__ighraw__isnull=True) | Q(repo_sched__ighenrich__isnull=True))\
            .filter(Q(repo_sched__ighenricharchived__isnull=False) | Q(repo_sched__ighrawarchived__isnull=False))
        gl = GitLabRepository.objects.filter(projects=self).filter(repo_sched__isnull=False)
        gl_running = gl.filter(Q(repo_sched__iglraw__isnull=False) | Q(repo_sched__iglenrich__isnull=False))
        gl_finish = gl.filter(Q(repo_sched__iglraw__isnull=True) | Q(repo_sched__iglenrich__isnull=True))\
            .filter(Q(repo_sched__iglenricharchived__isnull=False) | Q(repo_sched__iglrawarchived__isnull=False))
        meetup = MeetupRepository.objects.filter(projects=self).filter(repo_sched__isnull=False)
        meetup_running = meetup.filter(Q(repo_sched__imeetupraw__isnull=False) | Q(repo_sched__imeetupenrich__isnull=False))
        meetup_finish = meetup.filter(Q(repo_sched__imeetupraw__isnull=True) | Q(repo_sched__imeetupenrich__isnull=True))\
            .filter(Q(repo_sched__imeetupenricharchived__isnull=False) | Q(repo_sched__imeetuprawarchived__isnull=False))

        status = {
            'git': {'running': git_running, 'finish': git_finish},
            'github': {'running': gh_running, 'finish': gh_finish},
            'gitlab': {'running': gl_running, 'finish': gl_finish},
            'meetup': {'running': meetup_running, 'finish': meetup_finish}
        }
        return status

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
        odfe_api.update_elastic_role(self.projectrole.role, permissions)


class ProjectRole(models.Model):
    role = models.CharField(max_length=255, unique=True)
    backend_role = models.CharField(max_length=255, unique=True)
    project = models.OneToOneField(Project, on_delete=models.CASCADE, unique=True)

    def __str__(self):
        return f"{self.pk} - {self.role}, {self.project}"
