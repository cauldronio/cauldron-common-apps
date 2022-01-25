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
# https://github.com/chaoss/grimoirelab-sirmordred/blob/master/sirmordred/task_enrich.py
#
# In Cauldron we took autorefresh code and create or own class

import json
import logging
from datetime import datetime
from cauldron_apps.poolsched_utils.mordred.backend import Backend


try:
    from sirmordred.task import Task
    from sirmordred.task_projects import TaskProjects
    from sortinghat import api
    from sortinghat.db.database import Database
    from grimoire_elk.elk import refresh_identities
except ImportError:
    from cauldron_apps.poolsched_utils.mordred import sirmordred_fake
    Task = sirmordred_fake.Task
    TaskProjects = sirmordred_fake.TaskProjects


logger = logging.getLogger(__name__)

PROJECTS_FILE = '/tmp/tmp_projects.json'


class SHAutoRefresh(Backend):
    def __init__(self, datasource, last_autorefresh=None):
        super().__init__()
        self.datasource = datasource
        self.last_autorefresh = last_autorefresh or datetime.fromtimestamp(0)
        projects = {'Project': {}}
        with open(PROJECTS_FILE, 'w+') as f:
            json.dump(projects, f)
        self.config.set_param('projects', 'projects_file', PROJECTS_FILE)

    def run(self):
        """ Execute the refresh for this datasource."""
        TaskProjects(self.config).execute()

        task = TaskAutoRefresh(config=self.config,
                               backend_section=self.datasource,
                               last_autorefresh=self.last_autorefresh)
        try:
            task.execute()
            logger.info(f"Finish refreshing data for {self.datasource}.")
        except Exception as e:
            logger.error(f"Error refreshing data for {self.datasource}. Cause: {e}")
            raise e


class TaskAutoRefresh(Task):

    def __init__(self, config, backend_section=None, last_autorefresh=None):
        super().__init__(config)
        self.backend_section = backend_section
        if self.db_sh is None and self.db_host is None:
            self.db = None
        else:
            self.db = Database(**self.sh_kwargs)
        if last_autorefresh:
            self.last_autorefresh = last_autorefresh
        else:
            self.last_autorefresh = datetime.datetime.fromtimestamp(0)

    def __autorefresh(self, enrich_backend):
        # Refresh projects
        field_id = enrich_backend.get_field_unique_id()

        # Refresh identities
        logger.info("[%s] Refreshing identities", self.backend_section)
        logger.info(f'Getting last modified identities from SH since '
                    f'{self.last_autorefresh} for {self.backend_section}')
        uuids_refresh = api.search_last_modified_unique_identities(self.db, self.last_autorefresh)
        ids_refresh = api.search_last_modified_identities(self.db, self.last_autorefresh)
        author_fields = ["author_uuid"]
        try:
            meta_fields = enrich_backend.meta_fields
            author_fields += meta_fields
        except AttributeError:
            pass

        if uuids_refresh:
            logger.info(f"Refreshing {len(uuids_refresh)} uuid identities for {self.backend_section}")
            eitems = refresh_identities(enrich_backend, author_fields=author_fields, author_values=uuids_refresh)
            enrich_backend.elastic.bulk_upload(eitems, field_id)
        else:
            logger.info("No uuids to be refreshed found")
        if ids_refresh:
            logger.info(f"Refreshing {len(ids_refresh)} identity ids for {self.backend_section}")
            eitems = refresh_identities(enrich_backend, author_fields=author_fields, author_values=ids_refresh)
            enrich_backend.elastic.bulk_upload(eitems, field_id)
        else:
            logger.info("No ids to be refreshed found")

    def execute(self):
        """Execute autorefresh"""
        try:
            if self.db:
                logger.info('[%s] refresh start', self.backend_section)
                self.__autorefresh(self._get_enrich_backend())
                logger.info('[%s] refresh end', self.backend_section)
            else:
                logger.info('[%s] refresh not active', self.backend_section)

        except Exception as e:
            raise e
        finally:
            self.db._engine.dispose()
