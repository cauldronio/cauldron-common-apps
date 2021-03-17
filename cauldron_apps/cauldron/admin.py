import csv

from django.contrib import admin
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model

from cauldron_apps.poolsched_gitlab.models import GLInstance
from .models import IAddGHOwner, IAddGLOwner, IAddGHOwnerArchived, IAddGLOwnerArchived, \
    Project, Repository, GitRepository, GitHubRepository, GitLabRepository, MeetupRepository, \
    StackExchangeRepository, UserWorkspace, ProjectRole, AnonymousUser, OauthUser, AuthorizedBackendUser, \
    BannerMessage


User = get_user_model()


def user_name(obj):
    try:
        return obj.user.first_name
    except AttributeError:
        return None


def previous_count(obj):
    return obj.previous.count()


class ProjectDataSources(admin.SimpleListFilter):
    title = _('data sources')

    parameter_name = 'with_datasources'

    def lookups(self, request, model_admin):
        return (
            ('Yes', _('With data sources')),
            ('No', _('Without data sources')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'Yes':
            return queryset.exclude(repository__isnull=True)
        elif self.value() == 'No':
            return queryset.filter(repository__isnull=True)
        else:
            return queryset


class IsAnonymousUser(admin.SimpleListFilter):
    title = _('is authenticated')

    parameter_name = 'is_authenticated'

    def lookups(self, request, model_admin):
        return (
            ('Yes', _('Authenticated user')),
            ('No', _('Anonymous user')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'No':
            return queryset.filter(anonymoususer__isnull=False)
        elif self.value() == 'Yes':
            return queryset.filter(anonymoususer__isnull=True)
        else:
            return queryset


class UserAdmin(admin.ModelAdmin):
    list_filter = ('is_staff', IsAnonymousUser)
    search_fields = ('id', 'first_name')

    def get_list_display(self, request):
        display = ['id', 'first_name', 'is_staff', 'authenticated_user', 'num_projects',
                   'gh_token', 'meetup_token', 'stack_token']
        for instance in GLInstance.objects.values_list('name', flat=True):
            def _fn(obj, inst=instance):
                return obj.gltokens.filter(instance=inst).exists()
            _fn.short_description = f'{instance} Token'
            _fn.boolean = True
            display.append(_fn)
        return display

    def authenticated_user(self, obj):
        return not hasattr(obj, 'anonymoususer')
    authenticated_user.boolean = True

    def gh_token(self, obj):
        return obj.ghtokens.exists()
    gh_token.boolean = True

    def meetup_token(self, obj):
        return obj.meetuptokens.exists()
    meetup_token.boolean = True

    def stack_token(self, obj):
        return obj.stackexchangetokens.exists()
    stack_token.boolean = True

    def num_projects(self, obj):
        return obj.project_set.count()

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_filter = ('created', ProjectDataSources)
    search_fields = ('id', 'name', 'creator__first_name')
    ordering = ('id',)
    actions = ['export_as_csv']

    def get_list_display(self, request):
        display = ['id', 'name', 'created', 'creator_name', 'git_repos', 'github_repos', 'meetup_repos', 'stack_repos']
        for instance in GLInstance.objects.values_list('name', flat=True):
            def _fn(obj, inst=instance):
                return GitLabRepository.objects.filter(projects=obj, instance=inst).count()
            _fn.short_description = f'{instance} repos'
            display.append(_fn)
        return display

    def creator_name(self, obj):
        try:
            return obj.creator.first_name
        except AttributeError:
            return None
    creator_name.admin_order_field = 'creator__first_name'

    def git_repos(self, obj):
        return GitRepository.objects.filter(projects=obj).count()

    def github_repos(self, obj):
        return GitHubRepository.objects.filter(projects=obj).count()

    def meetup_repos(self, obj):
        return MeetupRepository.objects.filter(projects=obj).count()

    def stack_repos(self, obj):
        return StackExchangeRepository.objects.filter(projects=obj).count()

    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = ['id', 'name', 'created', 'creator_name', 'Git', 'GitHub', 'Meetup', 'StackExchange']
        gl_instance_names = GLInstance.objects.values_list('name', flat=True)
        field_names.extend(gl_instance_names)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename={}.csv'.format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names)
        for obj in queryset:
            gl_instance_values = []
            for instance_name in gl_instance_names:
                instance = GLInstance.objects.get(name=instance_name)
                repos = GitLabRepository.objects.filter(projects=obj, instance=instance).count()
                gl_instance_values.append(repos)

            row_values = [
                obj.id,
                obj.name,
                obj.created,
                self.creator_name(obj),
                self.git_repos(obj),
                self.github_repos(obj),
                self.meetup_repos(obj),
                self.stack_repos(obj),
            ]
            row_values.extend(gl_instance_values)

            row = writer.writerow(row_values)

        return response

    export_as_csv.short_description = "Export Selected"

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'backend')
    list_filter = ('backend',)
    ordering = ('id',)


@admin.register(GitRepository)
class GitRepositoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'url', 'repo_sched', 'status', 'last_refresh')
    search_fields = ('id', 'url')
    ordering = ('id',)


@admin.register(GitHubRepository)
class GitHubRepositoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'repo', 'repo_sched', 'status', 'last_refresh')
    search_fields = ('id', 'owner', 'repo')
    ordering = ('id', )


@admin.register(GitLabRepository)
class GitLabRepositoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'owner', 'repo', 'repo_sched', 'status', 'last_refresh')
    search_fields = ('id', 'owner', 'repo')
    ordering = ('id', )


@admin.register(MeetupRepository)
class MeetupRepositoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'group', 'repo_sched', 'status', 'last_refresh')
    search_fields = ('id', 'group')
    ordering = ('id',)


@admin.register(StackExchangeRepository)
class StackExchangeRepositoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'site', 'tagged', 'repo_sched', 'status', 'last_refresh')
    search_fields = ('id', 'site', 'tagged')
    ordering = ('id',)


@admin.register(UserWorkspace)
class UserWorkspaceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_name', 'tenant_name', 'tenant_role', 'backend_role')
    search_fields = ('id', 'user__first_name', 'tenant_name')
    ordering = ('id',)

    def user_name(self, obj):
        try:
            return obj.user.first_name
        except AttributeError:
            return None


@admin.register(ProjectRole)
class ProjectRoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'role', 'backend_role', 'project')
    ordering = ('id',)


admin.site.register(AnonymousUser)


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
    search_fields = ('id', 'user__first_name', 'owner', 'project__name')
    list_filter = ('created', RunningInAWorker)
    ordering = ('created', )


@admin.register(IAddGHOwnerArchived, IAddGLOwnerArchived)
class ArchivedIntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'completed', user_name, 'status',
                    'arch_job', 'owner', 'project', 'commits', 'issues', 'forks', 'analyze')
    search_fields = ('id', 'user__first_name', 'status', 'owner', 'project__name')
    list_filter = ('status', 'created', 'completed')
    ordering = ('completed', )


@admin.register(OauthUser)
class OauthUserAdmin(admin.ModelAdmin):
    list_display = ('id', user_name, 'backend', 'username', 'photo')
    search_fields = ('id', 'backend', 'username', 'user__first_name')
    list_filter = ('backend',)


@admin.register(AuthorizedBackendUser)
class AuthorizedBackendUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'backend', 'username')
    search_fields = ('id', 'backend', 'username')
    list_filter = ('backend',)


@admin.register(BannerMessage)
class BannerMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'created', 'read_by_count')
    search_fields = ('id', 'message')
    list_filter = ('created',)

    def read_by_count(self, obj):
        return obj.read_by.count()
