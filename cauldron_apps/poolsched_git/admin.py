from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import GitRepo, IGitRaw, IGitEnrich, IGitRawArchived, IGitEnrichArchived, \
    IGitAutoRefresh, IGitAutoRefreshArchived


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


@admin.register(IGitRaw, IGitEnrich)
class IntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'repo_url', 'created', 'job', user_name, previous_count)
    search_fields = ('id', 'repo__url', 'user__first_name')
    list_filter = ('created', RunningInAWorker)
    ordering = ('created', )

    def repo_url(self, obj):
        return obj.repo.url


@admin.register(IGitRawArchived, IGitEnrichArchived)
class ArchivedIntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'repo_url', 'created', 'completed', user_name, 'status', 'arch_job', 'logs')
    search_fields = ('id', 'repo__url', 'user__first_name', 'status')
    list_filter = ('status', 'created', 'completed')
    ordering = ('completed', )

    def repo_url(self, obj):
        return obj.repo.url

    def logs(self, obj):
        try:
            log_id = obj.arch_job.logs.id
            url = "/logs/" + str(log_id)
            return format_html("<a href='{url}'>Show</a>", url=url)
        except AttributeError:
            return None

@admin.register(GitRepo)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'url', 'created')
    search_fields = ('id', 'url', 'repo')
    list_filter = ('created',)
    ordering = ('id', )


@admin.register(IGitAutoRefresh)
class AutoRefreshIntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'job', 'last_autorefresh', 'scheduled')
    list_filter = ('created', RunningInAWorker, 'last_autorefresh', 'scheduled')
    ordering = ('-scheduled', )


@admin.register(IGitAutoRefreshArchived)
class AutoRefreshArchivedIntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'completed', 'status', 'arch_job', 'logs')
    list_filter = ('status', 'created', 'completed')
    ordering = ('-completed', )

    def logs(self, obj):
        try:
            log_id = obj.arch_job.logs.id
            url = "/logs/" + str(log_id)
            return format_html("<a href='{url}'>Show</a>", url=url)
        except AttributeError:
            return None
