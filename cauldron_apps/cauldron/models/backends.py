from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class Backends(TextChoices):
    GIT = 'GI', _('Git')
    GITHUB = 'GH', _('GitHub')
    GITLAB = 'GL', _('GitLab')
    GNOME = 'GN', _('Gnome')
    KDE = 'KD', _('KDE')
    MEETUP = 'MU', _('Meetup')
    STACK_EXCHANGE = 'SE', _('StackExchange')
    UNKNOWN = 'UK', _('Unknown')
