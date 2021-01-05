from django.db import models
from django.conf import settings

from model_utils.managers import InheritanceManager


class Action(models.Model):
    """Actions are intentions requested by the user for a project.

    Actions are performed in order. Users can request to run an action,
    and it will create an intention for them, or they can request to run
    all the actions for a specific project and they will be run in order by
    created date.
    """
    # When the action was created
    created = models.DateTimeField(auto_now_add=True)
    # An action is created by a user
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                null=True, blank=True)
    # An action is created for a project
    project = models.ForeignKey('cauldron.project', on_delete=models.CASCADE)

    # Use a custom manager to manage inheritance in a simpler way
    objects = InheritanceManager()

    class Meta:
        verbose_name_plural = "Actions"
        abstract = False
