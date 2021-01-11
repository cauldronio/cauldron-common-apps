from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import IGLEnrich, IGLRaw, IGLRawArchived, IGLEnrichArchived, GLToken, GLRepo, \
    IGLIssueAutoRefresh, IGLMergeAutoRefresh, IGLMergeAutoRefreshArchived, IGLIssueAutoRefreshArchived


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


@admin.register(IGLRaw, IGLEnrich)
class GHGLIntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'repo_owner', 'repo_name', 'created', 'job', user_name, previous_count)
    search_fields = ('id', 'repo__owner', 'repo__repo', 'user__first_name')
    list_filter = ('created', RunningInAWorker)
    ordering = ('created', )

    def repo_owner(self, obj):
        return obj.repo.owner

    def repo_name(self, obj):
        return obj.repo.repo


@admin.register(IGLRawArchived, IGLEnrichArchived)
class GHGLArchivedIntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'repo_owner', 'repo_name', 'created', 'completed', user_name, 'status', 'arch_job')
    search_fields = ('id', 'repo__owner', 'repo__repo', 'user__first_name', 'status')
    list_filter = ('status', 'created', 'completed')
    ordering = ('completed', )

    def repo_owner(self, obj):
        return obj.repo.owner

    def repo_name(self, obj):
        return obj.repo.repo


@admin.register(GLRepo)
class GHGLRepositoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'repo', 'created')
    search_fields = ('id', 'owner', 'repo')
    list_filter = ('created',)
    ordering = ('id', )


@admin.register(GLToken)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'token', 'reset', user_name, 'job_count', 'instance_name')
    search_fields = ('id', 'user__first_name')
    list_filter = ('reset',)
    ordering = ('id',)

    def job_count(self, obj):
        return obj.jobs.count()

    def instance_name(self, obj):
        return obj.instance.name


@admin.register(IGLIssueAutoRefresh, IGLMergeAutoRefresh)
class AutoRefreshIntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'job', 'last_autorefresh', 'scheduled')
    list_filter = ('created', RunningInAWorker, 'last_autorefresh', 'scheduled')
    ordering = ('-scheduled', )


@admin.register(IGLIssueAutoRefreshArchived, IGLMergeAutoRefreshArchived)
class AutoRefreshArchivedIntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'completed', 'status', 'arch_job')
    list_filter = ('status', 'created', 'completed')
    ordering = ('-completed', )
