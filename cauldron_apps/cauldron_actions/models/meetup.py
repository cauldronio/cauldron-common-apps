from django.db import models
from .action import Action


class AddMeetupRepoAction(Action):
    """
    Repository requested by the user to be added to a project.

    This model inherits from Action, so it includes all its fields.
    """

    # ForeignKey to the UI repository that should be included
    repository = models.ForeignKey('cauldron.MeetupRepository', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Add Meetup repo actions"

    @property
    def name_ui(self):
        return f"Add <b>{self.repository.group}</b> meetup group"

    @property
    def data_source_ui(self):
        return 'meetup'


class RemoveMeetupRepoAction(Action):
    """
    Repository that the user deleted from the project.

    This model inherits from Action, so it includes all its fields.
    """

    # ForeignKey to the UI repository that the user removed from the project
    repository = models.ForeignKey('cauldron.MeetupRepository', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Remove Meetup repo actions"

    @property
    def name_ui(self):
        return f"Remove <b>{self.repository.group}</b> meetup group"

    @property
    def data_source_ui(self):
        return 'meetup'
