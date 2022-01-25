#
# Copyright (C) 2015-2019 Bitergia
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
# For Cauldron we have updated all the code from
# https://github.com/chaoss/grimoirelab-sirmordred/blob/master/sirmordred/task_identities.py
#

import json
import logging
from cauldron_apps.poolsched_utils.mordred.backend import Backend


try:
    from sirmordred.task import Task
    from sirmordred.task_projects import TaskProjects
    from sirmordred.task_identities import TaskIdentitiesMerge
except ImportError:
    from cauldron_apps.poolsched_utils.mordred import sirmordred_fake
    Task = sirmordred_fake.Task
    TaskProjects = sirmordred_fake.TaskProjects


logger = logging.getLogger(__name__)

PROJECTS_FILE = '/tmp/tmp_projects.json'


class SHMergeIdentities(Backend):
    def __init__(self):
        super().__init__()
        projects = {'Project': {}}
        with open(PROJECTS_FILE, 'w+') as f:
            json.dump(projects, f)
        self.config.set_param('projects', 'projects_file', PROJECTS_FILE)

    def run(self):
        """ Execute the refresh for this datasource."""
        TaskProjects(self.config).execute()

        task = TaskIdentitiesMerge(self.config)
        try:
            task.execute()
            logger.info(f"Finish merging identities.")
        except Exception as e:
            logger.error(f"Error merging identities. Cause: {e}")
            raise e
        finally:
            if task.db:
                task.db._engine.dispose()
