from .git import ExportGit
from .github import ExportGitHub
from .gitlab import ExportGitLab
from .meetup import ExportMeetup
from .stack_exchange import ExportStackExchange

from cauldron_apps.cauldron.models.backends import Backends

backend_export = {
    Backends.GIT.value: ExportGit,
    Backends.GITHUB.value: ExportGitHub,
    Backends.GITLAB.value: ExportGitLab,
    Backends.GNOME.value: ExportGitLab,
    Backends.KDE.value: ExportGitLab,
    Backends.MEETUP.value: ExportMeetup,
    Backends.STACK_EXCHANGE.value: ExportStackExchange
}
