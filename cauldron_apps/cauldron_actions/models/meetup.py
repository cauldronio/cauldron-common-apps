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


class RemoveMeetupRepoAction(Action):
    """
    Repository that the user deleted from the project.

    This model inherits from Action, so it includes all its fields.
    """

    # ForeignKey to the UI repository that the user removed from the project
    repository = models.ForeignKey('cauldron.MeetupRepository', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Remove Meetup repo actions"
