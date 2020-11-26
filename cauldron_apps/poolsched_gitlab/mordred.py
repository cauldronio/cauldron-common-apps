import logging
import json
import math
import traceback
import sqlalchemy

try:
    from sirmordred.config import Config
    from sirmordred.task_projects import TaskProjects
    from sirmordred.task_collection import TaskRawDataCollection
    from sirmordred.task_enrich import TaskEnrich
except ImportError:
    from cauldron_apps.poolsched_utils.mordred import sirmordred_fake
    Config = sirmordred_fake.Config
    TaskProjects = sirmordred_fake.TaskProjects
    TaskRawDataCollection = sirmordred_fake.TaskRawDataCollection
    TaskEnrich = sirmordred_fake.TaskEnrich

from cauldron_apps.poolsched_utils.mordred.backend import Backend


logger = logging.getLogger(__name__)

PROJECTS_FILE = '/tmp/tmp_projects.json'
BACKEND_SECTIONS = ['gitlab:issue', 'gitlab:merge']


class GitLabRaw(Backend):
    def __init__(self, url, token):
        super().__init__()
        projects = {'Project': {}}
        for section in BACKEND_SECTIONS:
            projects['Project'][section] = [url]

        with open(PROJECTS_FILE, 'w+') as f:
            json.dump(projects, f)

        for section in BACKEND_SECTIONS:
            self.config.set_param(section, 'api-token', token)
        self.config.set_param('projects', 'projects_file', PROJECTS_FILE)

    def run(self):
        """ Execute the analysis for this backend.
        Return 0 or None for success, 1 for error, other for time to reset in minutes
        """
        TaskProjects(self.config).execute()
        for section in BACKEND_SECTIONS:
            task = TaskRawDataCollection(self.config, backend_section=section)

            try:
                out_repos = task.execute()
                repo = out_repos[0]
                if 'error' in repo and repo['error']:
                    logger.error(repo['error'])
                    if repo['error'].startswith('RateLimitError'):
                        seconds_to_reset = float(repo['error'].split(' ')[-1])
                        restart_minutes = math.ceil(seconds_to_reset / 60) + 2
                        logger.warning("RateLimitError. This task will be restarted in: "
                                       "{} minutes".format(restart_minutes))
                        return restart_minutes
                    return 1

            except Exception as e:
                logger.error("Error in raw data retrieval from {}. Cause: {}".format(section, e))
                traceback.print_exc()
                return 1


class GitLabEnrich(Backend):
    def __init__(self, url):
        super().__init__()
        projects = {'Project': {}}
        for section in BACKEND_SECTIONS:
            projects['Project'][section] = [url]
        with open(PROJECTS_FILE, 'w+') as f:
            json.dump(projects, f)
        self.config.set_param('projects', 'projects_file', PROJECTS_FILE)

    def run(self):
        """ Execute the analysis for this backend.
        Return 0 or None for success, 1 for error
        """
        TaskProjects(self.config).execute()
        for section in BACKEND_SECTIONS:
            task = None
            while not task:
                try:
                    task = TaskEnrich(self.config, backend_section=section)
                except sqlalchemy.exc.InternalError:
                    # There is a race condition in the code
                    task = None

            try:
                task.execute()
            except Exception as e:
                logger.warning("Error enriching data for {}. Cause: {}".format(section, e))
                traceback.print_exc()
                return 1
