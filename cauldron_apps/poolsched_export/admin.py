from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import IExportCSV, IExportCSVArchived, ProjectExportFile, \
                    IReportKbn, IReportKbnArchived, ProjectKibanaReport, \
                    ICommitsByWeek, ICommitsByWeekArchived, ReportsCommitsByWeek


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


@admin.register(IExportCSV)
class IntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'backend', 'created', 'job', user_name, previous_count)
    search_fields = ('id', 'project', 'user__first_name')
    list_filter = ('created', 'backend', RunningInAWorker)
    ordering = ('created', )


@admin.register(IExportCSVArchived)
class ArchivedIntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'backend', 'created', 'completed', user_name, 'status', 'arch_job', 'logs')
    search_fields = ('id', 'project', 'backend', 'user__first_name', 'status')
    list_filter = ('status', 'created', 'completed')
    ordering = ('completed', )

    def logs(self, obj):
        try:
            log_id = obj.arch_job.logs.id
            url = "/logs/" + str(log_id)
            return format_html("<a href='{url}'>Show</a>", url=url)
        except AttributeError:
            return None


@admin.register(ProjectExportFile)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'backend', 'created', 'location')
    search_fields = ('id', 'project', 'backend', 'created', 'location')
    list_filter = ('created',)
    ordering = ('id', )


@admin.register(IReportKbn)
class IntentionKbnAdmin(admin.ModelAdmin):
    list_display = ('id', 'kbn_report', 'created', 'job', user_name, previous_count)
    search_fields = ('id', 'kbn_report', 'user__first_name')
    list_filter = ('created', RunningInAWorker)
    ordering = ('created', )


@admin.register(IReportKbnArchived)
class ArchivedIntentionKbnAdmin(admin.ModelAdmin):
    list_display = ('id', 'kbn_report', 'created', 'completed', user_name, 'status', 'arch_job', 'logs')
    search_fields = ('id', 'kbn_report', 'user__first_name', 'status')
    list_filter = ('status', 'created', 'completed')
    ordering = ('completed', )

    def logs(self, obj):
        try:
            log_id = obj.arch_job.logs.id
            url = "/logs/" + str(log_id)
            return format_html("<a href='{url}'>Show</a>", url=url)
        except AttributeError:
            return None


@admin.register(ProjectKibanaReport)
class KibanaReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'from_date', 'to_date', 'location')
    search_fields = ('id', 'project', 'from_date', 'to_date', 'location')
    ordering = ('id', )


@admin.register(ICommitsByWeek)
class IntentionCommitsAdmin(admin.ModelAdmin):
    list_display = ('id', 'progress', 'created', 'job', user_name, previous_count)
    search_fields = ('id', 'user__first_name')
    list_filter = ('created', RunningInAWorker)
    ordering = ('created', )


@admin.register(ICommitsByWeekArchived)
class ArchivedIntentionCommitsAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'completed', user_name, 'status', 'arch_job', 'logs')
    search_fields = ('id', 'user__first_name', 'status')
    list_filter = ('status', 'created', 'completed')
    ordering = ('completed', )

    def logs(self, obj):
        try:
            log_id = obj.arch_job.logs.id
            url = "/logs/" + str(log_id)
            return format_html("<a href='{url}'>Show</a>", url=url)
        except AttributeError:
            return None


@admin.register(ReportsCommitsByWeek)
class ReportsCommitsByWeekAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'location_commits', 'location_authors')
    search_fields = ('id', )
    ordering = ('id', )

