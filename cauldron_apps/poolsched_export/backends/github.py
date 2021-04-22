from .base import ExportOpenDistroBackend


class ExportGitHub(ExportOpenDistroBackend):
    BASE_FIELDS = ['repository', 'id', 'pull_request', 'url', 'created_at', 'closed_at', 'state',
                   'author_uuid', 'assignee_data_uuid']
    SORTINGHAT_FIELDS = ['user_name', 'user_org', 'user_location', 'assignee_login', 'assignee_domain',
                         'assignee_data_org_name', 'author_domain', 'author_name', 'author_org_name']
    ES_INDEX = 'github'
