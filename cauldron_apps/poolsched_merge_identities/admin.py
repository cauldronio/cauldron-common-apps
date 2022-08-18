from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import IMergeIdentities, IMergeIdentitiesArchived


def user_name(obj):
    try:
        return obj.user.first_name
    except AttributeError:
        return None


def previous_count(obj):
    return obj.previous.count()


class RunningInAWorker(admin.SimpleListFilter):
    title = _('running in a worker')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'in_worker'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('Yes', _('Running in a worker')),
            ('No', _('Not running in a worker')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Check if there is a Job with a worker and compare with the filter.
        if self.value() == 'Yes':
            return queryset.filter(job__isnull=False, job__worker__isnull=False)
        else:
            return queryset


@admin.register(IMergeIdentities)
class MeetupIntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'scheduled', 'job', user_name, previous_count)
    search_fields = ('id', 'repo__repo', 'user__first_name')
    list_filter = ('created', RunningInAWorker)
    ordering = ('created', )

    def repo_group(self, obj):
        return obj.repo.repo


@admin.register(IMergeIdentitiesArchived)
class MeetArchivedIntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'scheduled', 'completed', user_name, 'status', 'arch_job', 'logs')
    search_fields = ('id', 'repo__repo', 'user__first_name', 'status')
    list_filter = ('status', 'created', 'completed')
    ordering = ('completed', )

    def repo_group(self, obj):
        return obj.repo.repo

    def logs(self, obj):
        try:
            log_id = obj.arch_job.logs.id
            url = "/logs/" + str(log_id)
            return format_html("<a href='{url}'>Show</a>", url=url)
        except AttributeError:
            return None
