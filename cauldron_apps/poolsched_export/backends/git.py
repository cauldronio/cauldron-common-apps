from .base import ExportOpenDistroBackend


class ExportGit(ExportOpenDistroBackend):
    BASE_FIELDS = ['hash', 'repo_name', 'author_uuid', 'author_domain', 'author_date', 'utc_author', 'tz',
                   'commit_date', 'utc_commit', 'committer_domain', 'files', 'lines_added', 'lines_removed']
    SORTINGHAT_FIELDS = ['author_name', 'author_org_name']
    ES_INDEX = 'git'
