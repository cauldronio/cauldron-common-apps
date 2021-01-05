from django.db import models
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


class AddGitLabRepoAction(Action):
    """
    Repository requested by the user to be added to a project.

    This model inherits from Action, so it includes all its fields.
    """

    # ForeignKey to the UI repository that should be included
    repository = models.ForeignKey('cauldron.GitLabRepository', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Add GitLab repo actions"


class RemoveGitLabRepoAction(Action):
    """
    Repository that the user deleted from the project.

    This model inherits from Action, so it includes all its fields.
    """

    # ForeignKey to the UI repository that the user removed from the project
    repository = models.ForeignKey('cauldron.GitLabRepository', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Remove GitLab repo actions"
