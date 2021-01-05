from django.contrib import admin
from . import models


def creator_name(obj):
    try:
        return obj.creator.first_name
    except AttributeError:
        return None


@admin.register(models.Action)
class ActionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', creator_name, 'project')
    search_fields = ('id', 'creator__first_name', 'project__id')
    list_filter = ('created',)


@admin.register(models.AddGitLabOwnerAction, models.AddGitHubOwnerAction)
class AddOwnerActionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', creator_name, 'project', 'commits', 'issues', 'forks')
    search_fields = ('id', 'creator__first_name', 'project__id')
    list_filter = ('created',)


@admin.register(models.AddGitRepoAction, models.AddGitHubRepoAction,
                models.AddGitLabRepoAction, models.AddMeetupRepoAction)
class AddRepoActionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', creator_name, 'project', 'repository')
    search_fields = ('id', 'creator__first_name', 'project__id')
    list_filter = ('created',)


@admin.register(models.RemoveGitRepoAction, models.RemoveMeetupRepoAction,
                models.RemoveGitHubRepoAction, models.RemoveGitLabRepoAction)
class RemoveRepoActionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', creator_name, 'project', 'repository')
    search_fields = ('id', 'creator__first_name', 'project__id')
    list_filter = ('created',)
