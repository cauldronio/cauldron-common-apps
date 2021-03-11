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

    @property
    def name_ui(self):
        return f"Add <b>{self.repository.url}</b> git repository"

    @property
    def data_source_ui(self):
        return 'git'

    def run(self):
        self.repository.projects.add(self.project)


class RemoveGitRepoAction(Action):
    """
    Repository that the user deleted from the project.

    This model inherits from Action, so it includes all its fields.
    """

    # ForeignKey to the UI repository that the user removed from the project
    repository = models.ForeignKey('cauldron.GitRepository', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Remove Git repo actions"

    @property
    def name_ui(self):
        return f"Remove <b>{self.repository.url}</b> git repository"

    @property
    def data_source_ui(self):
        return 'git'

    def run(self):
        self.repository.projects.remove(self.project)
