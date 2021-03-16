from django.db import models
from .action import Action


class AddStackExchangeRepoAction(Action):
    """
    Repository requested by the user to be added to a project.

    This model inherits from Action, so it includes all its fields.
    """

    # ForeignKey to the UI repository that should be included
    repository = models.ForeignKey('cauldron.StackExchangeRepository', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Add StackExchange repo actions"

    @property
    def name_ui(self):
        return f"Add group {self.repository.group}"

    @property
    def data_source_ui(self):
        return 'stackexchange'

    def run(self):
        self.repository.projects.add(self.project)


class RemoveStackExchangeRepoAction(Action):
    """
    Repository that the user deleted from the project.

    This model inherits from Action, so it includes all its fields.
    """

    # ForeignKey to the UI repository that the user removed from the project
    repository = models.ForeignKey('cauldron.StackExchangeRepository', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Remove StackExchange repo actions"

    @property
    def name_ui(self):
        return f"Remove group {self.repository.group}"

    @property
    def data_source_ui(self):
        return 'stackexchange'

    def run(self):
        self.repository.projects.remove(self.project)
