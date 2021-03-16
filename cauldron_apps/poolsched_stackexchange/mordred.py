import json
import logging
import math
import traceback

import sqlalchemy

from cauldron_apps.poolsched_utils.mordred.backend import Backend

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

logger = logging.getLogger(__name__)

PROJECTS_FILE = '/tmp/tmp_projects.json'
BACKEND_SECTION = 'stackexchange'


class StackExchangeRaw(Backend):
    def __init__(self, url, token, api_key):
        super().__init__()
        projects = {'Project': {}}
        projects['Project'][BACKEND_SECTION] = [url]
        with open(PROJECTS_FILE, 'w+') as f:
            json.dump(projects, f)
        self.config.set_param(BACKEND_SECTION, 'api-token', api_key)
        self.config.set_param(BACKEND_SECTION, 'access-token', token)
        self.config.set_param('projects', 'projects_file', PROJECTS_FILE)

    def run(self):
        """ Execute the analysis for this backend.
        Return 0 or None for success, 1 for error, other for time to reset in minutes
        """
        TaskProjects(self.config).execute()

        task = TaskRawDataCollection(self.config, backend_section=BACKEND_SECTION)
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
            logger.error("Error in raw data retrieval from StackExchange. Cause: {}".format(e))
            traceback.print_exc()
            return 1


class StackExchangeEnrich(Backend):
    def __init__(self, url):
        super().__init__()
        projects = {'Project': {}}
        projects['Project'][BACKEND_SECTION] = [url]
        with open(PROJECTS_FILE, 'w+') as f:
            json.dump(projects, f)
        self.config.set_param('projects', 'projects_file', PROJECTS_FILE)

    def run(self):
        """ Execute the analysis for this backend.
        Return 0 or None for success, 1 for error
        """
        TaskProjects(self.config).execute()
        task = None
        while not task:
            try:
                task = TaskEnrich(self.config, backend_section=BACKEND_SECTION)
            except sqlalchemy.exc.InternalError:
                task = None

        try:
            task.execute()
        except Exception as e:
            logger.warning("Error enriching data for StackExchange. Cause: {}".format(e))
            traceback.print_exc()
            return 1
