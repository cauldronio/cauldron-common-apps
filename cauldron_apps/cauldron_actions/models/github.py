from django.db import models
from .action import Action


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


class AddGitHubRepoAction(Action):
    """
    Repository requested by the user to be added to a project.

    This model inherits from Action, so it includes all its fields.
    """

    # ForeignKey to the UI repository that should be included
    repository = models.ForeignKey('cauldron.GitHubRepository', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Add GitHub repo actions"


class RemoveGitHubRepoAction(Action):
    """
    Repository that the user deleted from the project.

    This model inherits from Action, so it includes all its fields.
    """

    # ForeignKey to the UI repository that the user removed from the project
    repository = models.ForeignKey('cauldron.GitHubRepository', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Remove GitHub repo actions"
