import ssl
from django.db import models
from django.utils.timezone import now
from django.apps import apps

from .backends import Backends
from cauldron_apps.poolsched_git import models as git_models
from cauldron_apps.poolsched_git import api as git_api
from cauldron_apps.poolsched_github import models as github_models
from cauldron_apps.poolsched_github import api as github_api
from cauldron_apps.poolsched_gitlab import models as gitlab_models
from cauldron_apps.poolsched_gitlab import api as gitlab_api
from cauldron_apps.poolsched_meetup import models as meetup_models
from cauldron_apps.poolsched_meetup import api as meetup_api
from cauldron_apps.poolsched_stackexchange import models as stack_models
from cauldron_apps.poolsched_stackexchange import api as stack_api

from poolsched import models as sched_models

from model_utils.managers import InheritanceManager


class Repository(models.Model):
    # Globals for the state of a repository
    IN_PROGRESS = 'In progress'
    ANALYZED = 'Analyzed'
    ERROR = 'Error'
    PENDING = 'Pending'

    objects = InheritanceManager()

    projects = models.ManyToManyField('cauldron.project')
    metrics = models.ForeignKey('cauldron.RepositoryMetrics', on_delete=models.SET_NULL, null=True, default=None)
    backend = models.CharField(
        max_length=2,
        choices=Backends.choices,
        default=Backends.UNKNOWN,
    )
    last_refresh = models.DateTimeField(default=None, null=True)

    class Meta:
        verbose_name_plural = "Repositories"

    def __str__(self):
        return f"{self.pk} - {self.get_backend_display()}"

    @property
    def status(self):
        """Return running, pending or unknown depending on the status"""
        raise NotImplementedError

    @property
    def datasource_url(self):
        """Return the URL as in sirmordred configuration"""
        raise NotImplementedError

    @property
    def repository_link(self):
        """Return a link to the repository"""
        raise NotImplementedError

    def remove_intentions(self, user):
        raise NotImplementedError

    def refresh(self, user):
        """Try to refresh the repository.
        Return whether the repository is going to be refreshed or not"""
        raise NotImplementedError

    def create_remove_action(self, project):
        """Create action of removing a repository from a project"""
        raise NotImplementedError

    def update_last_refresh(self):
        self.last_refresh = now()
        self.save()


class GitRepository(Repository):
    url = models.CharField(max_length=255, unique=True)
    parent = models.OneToOneField(to=Repository, on_delete=models.CASCADE, parent_link=True, related_name='git')
    repo_sched = models.OneToOneField(git_models.GitRepo, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name_plural = "Git repositories"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend = Backends.GIT

    def __str__(self):
        return f"{self.pk} - ...{self.url[-20:]}"

    def link_sched_repo(self):
        if not self.repo_sched:
            repo_sched, _ = git_models.GitRepo.objects.get_or_create(url=self.url)
            self.repo_sched = repo_sched
            self.save()

    @property
    def datasource_url(self):
        return self.url

    @property
    def repository_link(self):
        return self.url

    def refresh(self, user):
        """Try to refresh the repository.
        Return whether the repository is going to be refreshed or not"""
        return git_api.analyze_git_repo_obj(user, self.repo_sched)

    @property
    def status(self):
        """Return status of the repository"""
        intentions = self.repo_sched.igitraw_set.count() + \
                     self.repo_sched.igitenrich_set.count()
        if intentions > 0:
            in_progress = self.repo_sched.igitraw_set.filter(job__worker__isnull=False).count() + \
                          self.repo_sched.igitenrich_set.filter(job__worker__isnull=False).count()
            if in_progress:
                return self.IN_PROGRESS
            else:
                return self.PENDING
        try:
            enrich = self.repo_sched.igitenricharchived_set\
                .latest('completed')
            raw = self.repo_sched.igitrawarchived_set\
                .latest('completed')
            ok = (enrich.status == sched_models.ArchivedIntention.OK) and \
                 (raw.status == sched_models.ArchivedIntention.OK)
        except git_models.IGitEnrichArchived.DoesNotExist:
            ok = False

        if ok:
            return self.ANALYZED
        else:
            return self.ERROR

    def get_intentions(self):
        """Return a list of intentions related with this object"""
        intentions = list(self.repo_sched.igitraw_set.all()) + list(self.repo_sched.igitenrich_set.all())
        arch_intentions = list(self.repo_sched.igitrawarchived_set.all()) + list(self.repo_sched.igitenricharchived_set.all())
        intentions_sorted = sorted(intentions, key=lambda item: item.created, reverse=True)
        arch_intentions_sorted = sorted(arch_intentions, key=lambda item: item.completed, reverse=True)
        return {'intentions': intentions_sorted, 'arch_intentions': arch_intentions_sorted[:4]}

    def remove_intentions(self, user):
        """Remove all the intentions of this user related with this repository"""
        self.repo_sched.igitraw_set.filter(user=user, job=None).delete()
        self.repo_sched.igitenrich_set.filter(user=user, job=None).delete()

    def create_remove_action(self, project):
        """Create action of removing a repository from a project"""
        RemoveGitRepoAction = apps.get_model('cauldron_actions.RemoveGitRepoAction')
        RemoveGitRepoAction.objects.create(project=project, creator=project.creator,
                                                         repository=self)


class GitHubRepository(Repository):
    owner = models.CharField(max_length=40)
    repo = models.CharField(max_length=100)
    parent = models.OneToOneField(to=Repository, on_delete=models.CASCADE, parent_link=True, related_name='github')
    repo_sched = models.OneToOneField(github_models.GHRepo, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name_plural = "GitHub repositories"
        unique_together = ('owner', 'repo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend = Backends.GITHUB

    def __str__(self):
        return f"{self.pk} - {self.owner}/{self.repo}"

    def link_sched_repo(self):
        if not self.repo_sched:
            instance = github_models.GHInstance.objects.get(name='GitHub')
            repo_sched, _ = github_models.GHRepo.objects.get_or_create(owner=self.owner, repo=self.repo,
                                                                instance=instance)
            self.repo_sched = repo_sched
            self.save()

    @property
    def datasource_url(self):
        return f"https://github.com/{self.owner}/{self.repo}"

    @property
    def repository_link(self):
        return f"https://github.com/{self.owner}/{self.repo}"

    def refresh(self, user):
        """Try to refresh the repository.
        Return whether the repository is going to be refreshed or not"""
        return github_api.analyze_gh_repo_obj(user, self.repo_sched)

    @property
    def status(self):
        """Return status of the repository"""
        intentions = self.repo_sched.ighraw_set.count() + \
                     self.repo_sched.ighenrich_set.count()
        if intentions > 0:
            in_progress = self.repo_sched.ighraw_set.filter(job__worker__isnull=False).count() + \
                          self.repo_sched.ighenrich_set.filter(job__worker__isnull=False).count()
            if in_progress:
                return self.IN_PROGRESS
            else:
                return self.PENDING
        try:
            enrich = self.repo_sched.ighenricharchived_set\
                .latest('completed')
            raw = self.repo_sched.ighrawarchived_set\
                .latest('completed')
            ok = (enrich.status == sched_models.ArchivedIntention.OK) and \
                 (raw.status == sched_models.ArchivedIntention.OK)
        except github_models.IGHEnrichArchived.DoesNotExist:
            ok = False

        if ok:
            return self.ANALYZED
        else:
            return self.ERROR

    def get_intentions(self):
        """Return a list of intentions related with this object"""
        intentions = list(self.repo_sched.ighraw_set.all()) + list(self.repo_sched.ighenrich_set.all())
        arch_intentions = list(self.repo_sched.ighrawarchived_set.all()) + list(self.repo_sched.ighenricharchived_set.all())
        intentions_sorted = sorted(intentions, key=lambda item: item.created, reverse=True)
        arch_intentions_sorted = sorted(arch_intentions, key=lambda item: item.completed, reverse=True)
        return {'intentions': intentions_sorted, 'arch_intentions': arch_intentions_sorted[:4]}

    def remove_intentions(self, user):
        """Remove all the intentions of this user related with this repository"""
        self.repo_sched.ighraw_set.filter(user=user, job=None).delete()
        self.repo_sched.ighenrich_set.filter(user=user, job=None).delete()

    def create_remove_action(self, project):
        """Create action of removing a repository from a project"""
        RemoveGitHubRepoAction = apps.get_model('cauldron_actions.RemoveGitHubRepoAction')
        RemoveGitHubRepoAction.objects.create(project=project, creator=project.creator,
                                                            repository=self)


class GitLabRepository(Repository):
    owner = models.CharField(max_length=40)
    repo = models.CharField(max_length=100)
    instance = models.ForeignKey(gitlab_models.GLInstance, on_delete=models.SET_NULL,
                                 default='GitLab', null=True, blank=True,
                                 to_field='name')
    parent = models.OneToOneField(to=Repository, on_delete=models.CASCADE, parent_link=True, related_name='gitlab')
    repo_sched = models.OneToOneField(gitlab_models.GLRepo, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name_plural = "GitLab repositories"
        unique_together = ('owner', 'repo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.name == 'Gnome':
            self.backend = Backends.GNOME
        elif self.instance.name == 'KDE':
            self.backend = Backends.KDE
        else:
            self.backend = Backends.GITLAB

    def __str__(self):
        return f"{self.pk} - {self.owner}/{self.repo}"

    def link_sched_repo(self):
        if not self.repo_sched:
            repo_sched, _ = gitlab_models.GLRepo.objects.get_or_create(owner=self.owner, repo=self.repo,
                                                                       instance=self.instance)
            self.repo_sched = repo_sched
            self.save()

    @property
    def datasource_url(self):
        return f'{self.instance.endpoint}/{self.owner}/{self.repo}'

    @property
    def repository_link(self):
        return f'{self.instance.endpoint}/{self.owner}/{self.repo}'

    def refresh(self, user):
        """Try to refresh the repository.
        Return whether the repository is going to be refreshed or not"""
        return gitlab_api.analyze_gl_repo_obj(user, self.repo_sched)

    @property
    def status(self):
        """Return status of the repository"""
        intentions = self.repo_sched.iglraw_set.count() + \
                     self.repo_sched.iglenrich_set.count()
        if intentions > 0:
            in_progress = self.repo_sched.iglraw_set.filter(job__worker__isnull=False).count() + \
                          self.repo_sched.iglenrich_set.filter(job__worker__isnull=False).count()
            if in_progress:
                return self.IN_PROGRESS
            else:
                return self.PENDING
        try:
            enrich = self.repo_sched.iglenricharchived_set\
                .latest('completed')
            raw = self.repo_sched.iglrawarchived_set\
                .latest('completed')
            ok = (enrich.status == sched_models.ArchivedIntention.OK) and \
                 (raw.status == sched_models.ArchivedIntention.OK)
        except gitlab_models.IGLEnrichArchived.DoesNotExist:
            ok = False

        if ok:
            return self.ANALYZED
        else:
            return self.ERROR

    def get_intentions(self):
        """Return a list of intentions related with this object"""
        intentions = list(self.repo_sched.iglraw_set.all()) + list(self.repo_sched.iglenrich_set.all())
        arch_intentions = list(self.repo_sched.iglrawarchived_set.all()) + list(self.repo_sched.iglenricharchived_set.all())
        intentions_sorted = sorted(intentions, key=lambda item: item.created, reverse=True)
        arch_intentions_sorted = sorted(arch_intentions, key=lambda item: item.completed, reverse=True)
        return {'intentions': intentions_sorted, 'arch_intentions': arch_intentions_sorted[:4]}

    def remove_intentions(self, user):
        """Remove all the intentions of this user related with this repository"""
        self.repo_sched.iglraw_set.filter(user=user, job=None).delete()
        self.repo_sched.iglenrich_set.filter(user=user, job=None).delete()

    def create_remove_action(self, project):
        """Create action of removing a repository from a project"""
        RemoveGitLabRepoAction = apps.get_model('cauldron_actions.RemoveGitLabRepoAction')
        RemoveGitLabRepoAction.objects.create(project=project, creator=project.creator,
                                                            repository=self)


class MeetupRepository(Repository):
    group = models.CharField(max_length=100, unique=True)
    parent = models.OneToOneField(to=Repository, on_delete=models.CASCADE, parent_link=True, related_name='meetup')
    repo_sched = models.OneToOneField(meetup_models.MeetupRepo, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name_plural = "Meetup repositories"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend = Backends.MEETUP

    def __str__(self):
        return f"{self.pk} - {self.group}"

    def link_sched_repo(self):
        if not self.repo_sched:
            repo_sched, _ = meetup_models.MeetupRepo.objects.get_or_create(repo=self.group)
            self.repo_sched = repo_sched
            self.save()

    @property
    def datasource_url(self):
        return self.group

    @property
    def repository_link(self):
        return f"https://www.meetup.com/{self.group}"

    def refresh(self, user):
        """Try to refresh the repository.
        Return whether the repository is going to be refreshed or not"""
        return meetup_api.analyze_meetup_repo_obj(user, self.repo_sched)

    @property
    def status(self):
        """Return status of the repository"""
        intentions = self.repo_sched.imeetupraw_set.count() + \
                     self.repo_sched.imeetupenrich_set.count()
        if intentions > 0:
            in_progress = self.repo_sched.imeetupraw_set.filter(job__worker__isnull=False).count() + \
                        self.repo_sched.imeetupenrich_set.filter(job__worker__isnull=False).count()
            if in_progress:
                return self.IN_PROGRESS
            else:
                return self.PENDING
        try:
            enrich = self.repo_sched.imeetupenricharchived_set \
                .latest('completed')
            raw = self.repo_sched.imeetuprawarchived_set \
                .latest('completed')
            ok = (enrich.status == sched_models.ArchivedIntention.OK) and \
                 (raw.status == sched_models.ArchivedIntention.OK)
        except meetup_models.IMeetupEnrichArchived.DoesNotExist:
            ok = False

        if ok:
            return self.ANALYZED
        else:
            return self.ERROR

    def get_intentions(self):
        """Return a list of intentions related with this object"""
        intentions = list(self.repo_sched.imeetupraw_set.all()) + list(self.repo_sched.imeetupenrich_set.all())
        arch_intentions = list(self.repo_sched.imeetuprawarchived_set.all()) + list(self.repo_sched.imeetupenricharchived_set.all())
        intentions_sorted = sorted(intentions, key=lambda item: item.created, reverse=True)
        arch_intentions_sorted = sorted(arch_intentions, key=lambda item: item.completed, reverse=True)
        return {'intentions': intentions_sorted, 'arch_intentions': arch_intentions_sorted[:4]}

    def remove_intentions(self, user):
        """Remove all the intentions of this user related with this repository"""
        self.repo_sched.imeetupraw_set.filter(user=user, job=None).delete()
        self.repo_sched.imeetupenrich_set.filter(user=user, job=None).delete()

    def create_remove_action(self, project):
        """Create action of removing a repository from a project"""
        RemoveMeetupRepoAction = apps.get_model('cauldron_actions.RemoveMeetupRepoAction')
        RemoveMeetupRepoAction.objects.create(project=project, creator=project.creator,
                                                            repository=self)


class StackExchangeRepository(Repository):
    site = models.CharField(max_length=100)
    tagged = models.CharField(max_length=100)
    parent = models.OneToOneField(to=Repository, on_delete=models.CASCADE, parent_link=True, related_name='stackexchange')
    repo_sched = models.OneToOneField(stack_models.StackExchangeQuestionTag, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name_plural = "StackExchange tags"
        unique_together = ['site', 'tagged']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.backend = Backends.STACK_EXCHANGE

    def __str__(self):
        return f"{self.pk} - {self.site}/{self.tagged}"

    def link_sched_repo(self):
        if not self.repo_sched:
            repo_sched, _ = stack_models.StackExchangeQuestionTag.objects.get_or_create(site=self.site,
                                                                                        tagged=self.tagged)
            self.repo_sched = repo_sched
            self.save()

    @property
    def datasource_url(self):
        return self.repo_sched.url

    @property
    def repository_link(self):
        tags = self.repo_sched.tagged.replace(';', '+')
        return f'https://{self.site}/questions/tagged/{tags}'

    def refresh(self, user):
        """Try to refresh the repository.
        Return whether the repository is going to be refreshed or not"""
        return stack_api.analyze_stack_repo_obj(user, self.repo_sched)

    @property
    def status(self):
        """Return status of the repository"""
        intentions = self.repo_sched.istackexchangeraw_set.count() + \
                     self.repo_sched.istackexchangeenrich_set.count()
        if intentions > 0:
            in_progress = self.repo_sched.istackexchangeraw_set.filter(job__worker__isnull=False).count() + \
                        self.repo_sched.istackexchangeenrich_set.filter(job__worker__isnull=False).count()
            if in_progress:
                return self.IN_PROGRESS
            else:
                return self.PENDING
        try:
            enrich = self.repo_sched.istackexchangeenricharchived_set \
                .latest('completed')
            raw = self.repo_sched.istackexchangerawarchived_set \
                .latest('completed')
            ok = (enrich.status == sched_models.ArchivedIntention.OK) and \
                 (raw.status == sched_models.ArchivedIntention.OK)
        except stack_models.IStackExchangeEnrichArchived.DoesNotExist:
            ok = False

        if ok:
            return self.ANALYZED
        else:
            return self.ERROR

    def get_intentions(self):
        """Return a list of intentions related with this object"""
        intentions = list(self.repo_sched.istackexchangeraw_set.all()) + list(self.repo_sched.istackexchangeenrich_set.all())
        arch_intentions = list(self.repo_sched.istackexchangerawarchived_set.all()) + list(self.repo_sched.istackexchangeenricharchived_set.all())
        intentions_sorted = sorted(intentions, key=lambda item: item.created, reverse=True)
        arch_intentions_sorted = sorted(arch_intentions, key=lambda item: item.completed, reverse=True)
        return {'intentions': intentions_sorted, 'arch_intentions': arch_intentions_sorted[:4]}

    def remove_intentions(self, user):
        """Remove all the intentions of this user related with this repository"""
        self.repo_sched.istackexchangeraw_set.filter(user=user, job=None).delete()
        self.repo_sched.istackexchangeenrich_set.filter(user=user, job=None).delete()

    def create_remove_action(self, project):
        """Create action of removing a repository from a project"""
        RemoveStackExchangeRepoAction = apps.get_model('cauldron_actions.RemoveStackExchangeRepoAction')
        RemoveStackExchangeRepoAction.objects.create(project=project, creator=project.creator,
                                                     repository=self)
