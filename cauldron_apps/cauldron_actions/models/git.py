from django.db import models
from .action import Action


class AddGitRepoAction(Action):
    """
    Repository requested by the user to be added to a project.

    This model inherits from Action, so it includes all its fields.
    """

    # ForeignKey to the UI repository that should be included
    repository = models.ForeignKey('cauldron.GitRepository', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Add Git repo actions"


class RemoveGitRepoAction(Action):
    """
    Repository that the user deleted from the project.

    This model inherits from Action, so it includes all its fields.
    """

    # ForeignKey to the UI repository that the user removed from the project
    repository = models.ForeignKey('cauldron.GitRepository', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Remove Git repo actions"
