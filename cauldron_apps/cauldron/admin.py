from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import IAddGHOwner, IAddGLOwner, IAddGHOwnerArchived, IAddGLOwnerArchived


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


@admin.register(IAddGLOwner, IAddGHOwner)
class IntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'job', user_name, previous_count,
                    'owner', 'project', 'commits', 'issues', 'forks', 'analyze')
    search_fields = ('id', 'user__first_name', 'owner', 'project')
    list_filter = ('created', RunningInAWorker)
    ordering = ('created', )


@admin.register(IAddGHOwnerArchived, IAddGLOwnerArchived)
class ArchivedIntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'completed', user_name, 'status',
                    'arch_job', 'owner', 'project', 'commits', 'issues', 'forks', 'analyze')
    search_fields = ('id', 'user__first_name', 'status', 'owner', 'project')
    list_filter = ('status', 'created', 'completed')
    ordering = ('completed', )
