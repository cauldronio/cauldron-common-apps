import os
import tarfile
import logging

from .base import ExportOpenDistroBackend


logger = logging.getLogger(__name__)


def remove_file(filename):
    try:
        os.remove(filename)
    except OSError as e:
        logger.error(f'Error removing temporary file: {e}')
    else:
        logger.info(f"{filename} removed")


class ExportGitLabIssues(ExportOpenDistroBackend):
    BASE_FIELDS = ['repository', 'id', 'id_in_repo', 'state', 'created_at', 'closed_at',
                   'time_to_first_attention', 'author_username', 'assignee_username', 'milestone']
    SORTINGHAT_FIELDS = ['author_name', 'author_org_name', 'assignee_name']
    ES_INDEX = 'gitlab_issues'


class ExportGitLabMergeRequests(ExportOpenDistroBackend):
    BASE_FIELDS = ['repository', 'id', 'id_in_repo', 'state', 'created_at', 'closed_at', 'solved_at',
                   'time_to_first_attention', 'author_username', 'merge_author_login', 'milestone']
    SORTINGHAT_FIELDS = ['author_name', 'author_org_name', 'merge_author_name']
    ES_INDEX = 'gitlab_mrs'


class ExportGitLab:
    def __init__(self, project_role, es_host, es_port, es_scheme):
        self.project_role = project_role
        self.es_host = es_host
        self.es_port = es_port
        self.es_scheme = es_scheme

    def store_csv(self, file_path, compress=False, sortinghat=False):
        export_issues = ExportGitLabIssues(project_role=self.project_role,
                                           es_host=self.es_host,
                                           es_port=self.es_port,
                                           es_scheme=self.es_scheme)
        export_issues.store_csv(file_path='/tmp/gitlab_issues.csv',
                                compress=False,
                                sortinghat=sortinghat)

        export_mrs = ExportGitLabMergeRequests(project_role=self.project_role,
                                               es_host=self.es_host,
                                               es_port=self.es_port,
                                               es_scheme=self.es_scheme)
        export_mrs.store_csv(file_path='/tmp/gitlab_mrs.csv',
                             compress=False,
                             sortinghat=sortinghat)

        mode = 'w:gz' if compress else 'w'

        with tarfile.open(file_path, mode) as tar:
            tar.add('/tmp/gitlab_issues.csv', arcname='gitlab_issues.csv')
            tar.add('/tmp/gitlab_mrs.csv', arcname='gitlab_mrs.csv')

        remove_file('/tmp/gitlab_issues.csv')
        remove_file('/tmp/gitlab_mrs.csv')


