import logging
from django.db import models
from github import Github

from cauldron_apps.cauldron.models import GitRepository, GitHubRepository
from .action import Action

logger = logging.getLogger(__name__)


class AddGitHubOwnerAction(Action):
    """
    Data requested by the user when added an owner to the project.

    This model inherits from Action, so it includes all its fields.
    """

    # GitHub owner to get the repositories
    owner = models.CharField(max_length=128)
    # Collect git repositories
    commits = models.BooleanField(default=True)
    # Collect github repositories
    issues = models.BooleanField(default=True)
    # Collect forks
    forks = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Add GitHub owner actions"

    @property
    def name_ui(self):
        return f"Add <b>{self.owner}</b> github organization"

    @property
    def data_source_ui(self):
        return 'github'

    def run(self):
        token = self.creator.ghtokens.first()
        github = Github(token.token)
        repositories = github.get_user(self.owner).get_repos()
        for repo_gh in repositories:
            if repo_gh.fork and not self.forks:
                continue
            if self.issues:
                logger.info(f"Adding GitHub {self.owner}/{repo_gh.name} to project {self.project.id}")
                repo, created = GitHubRepository.objects.get_or_create(owner=self.owner, repo=repo_gh.name)
                if not repo.repo_sched:
                    repo.link_sched_repo()
                repo.projects.add(self.project)
            if self.commits:
                logger.info(f"Adding Git {repo_gh.clone_url} to project {self.project.id}")
                repo, created = GitRepository.objects.get_or_create(url=repo_gh.clone_url)
                if not repo.repo_sched:
                    repo.link_sched_repo()
                repo.projects.add(self.project)


class AddGitHubRepoAction(Action):
    """
    Repository requested by the user to be added to a project.

    This model inherits from Action, so it includes all its fields.
    """

    # ForeignKey to the UI repository that should be included
    repository = models.ForeignKey('cauldron.GitHubRepository', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Add GitHub repo actions"

    @property
    def name_ui(self):
        return f"Add <b>{self.repository.owner}/{self.repository.repo}</b> github repository"

    @property
    def data_source_ui(self):
        return 'github'

    def run(self):
        self.repository.projects.add(self.project)


class RemoveGitHubRepoAction(Action):
    """
    Repository that the user deleted from the project.

    This model inherits from Action, so it includes all its fields.
    """

    # ForeignKey to the UI repository that the user removed from the project
    repository = models.ForeignKey('cauldron.GitHubRepository', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Remove GitHub repo actions"

    @property
    def name_ui(self):
        return f"Remove <b>{self.repository.owner}/{self.repository.repo}</b> github repository"

    @property
    def data_source_ui(self):
        return 'github'

    def run(self):
        self.repository.projects.remove(self.project)
