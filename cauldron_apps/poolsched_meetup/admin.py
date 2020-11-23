from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import IMeetupRaw, IMeetupEnrich, IMeetupRawArchived, IMeetupEnrichArchived, MeetupRepo, MeetupToken


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


@admin.register(IMeetupRaw, IMeetupEnrich)
class MeetupIntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'repo_group', 'created', 'job', user_name, previous_count)
    search_fields = ('id', 'repo__repo', 'user__first_name')
    list_filter = ('created', RunningInAWorker)
    ordering = ('created', )

    def repo_group(self, obj):
        return obj.repo.repo


@admin.register(IMeetupRawArchived, IMeetupEnrichArchived)
class MeetArchivedIntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'repo_group', 'created', 'completed', user_name, 'status', 'arch_job')
    search_fields = ('id', 'repo__repo', 'user__first_name', 'status')
    list_filter = ('status', 'created', 'completed')
    ordering = ('completed', )

    def repo_group(self, obj):
        return obj.repo.repo


@admin.register(MeetupRepo)
class GitRepositoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'repo', 'created')
    search_fields = ('id', 'repo')
    list_filter = ('created',)
    ordering = ('id',)


@admin.register(MeetupToken)
class TokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'token', 'reset', user_name, 'job_count')
    search_fields = ('id', 'repo')
    list_filter = ('reset',)
    ordering = ('id',)

    def job_count(self, obj):
        return obj.jobs.count()
