from django.db import models

from cauldron_apps.cauldron.models import IAddGLOwner
from .action import Action


class AddGitLabOwnerAction(Action):
    """
    Data requested by the user when added an owner to the project.

    This model inherits from Action, so it includes all its fields.
    """

    # GitLab owner to get the repositories
    owner = models.CharField(max_length=128)
    # GitLab instance
    instance = models.ForeignKey('poolsched_gitlab.GLInstance', on_delete=models.CASCADE)
    # Collect git repositories
    commits = models.BooleanField(default=True)
    # Collect GitLab repositories
    issues = models.BooleanField(default=True)
    # Collect forks
    forks = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Add GitLab owner actions"

    @property
    def name_ui(self):
        return f"Add <b>{self.owner}</b> gitlab group"

    @property
    def data_source_ui(self):
        return self.instance.slug

    def run(self):
        owner_intention = IAddGLOwner(project=self.project, owner=self.owner, instance=self.instance,
                                      commits=self.commits, issues=self.issues, forks=self.forks,
                                      analyze=False)
        token = self.creator.gltokens.filter(instance=self.instance).first()
        owner_intention._run_owner(token.token)


class AddGitLabRepoAction(Action):
    """
    Repository requested by the user to be added to a project.

    This model inherits from Action, so it includes all its fields.
    """

    # ForeignKey to the UI repository that should be included
    repository = models.ForeignKey('cauldron.GitLabRepository', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Add GitLab repo actions"

    @property
    def name_ui(self):
        return f"Add <b>{self.repository.owner}/{self.repository.repo}</b> gitlab repository"

    @property
    def data_source_ui(self):
        return self.repository.instance.slug

    def run(self):
        self.repository.projects.add(self.project)


class RemoveGitLabRepoAction(Action):
    """
    Repository that the user deleted from the project.

    This model inherits from Action, so it includes all its fields.
    """

    # ForeignKey to the UI repository that the user removed from the project
    repository = models.ForeignKey('cauldron.GitLabRepository', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Remove GitLab repo actions"

    @property
    def name_ui(self):
        return f"Remove <b>{self.repository.owner}/{self.repository.repo}</b> gitlab repository"

    @property
    def data_source_ui(self):
        return self.repository.instance.slug

    def run(self):
        self.repository.projects.remove(self.project)
