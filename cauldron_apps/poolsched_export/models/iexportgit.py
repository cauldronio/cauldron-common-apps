import datetime
import logging
import os
import ssl
import csv

from django.db import models, transaction
from django.conf import settings

try:
    from elasticsearch import Elasticsearch
    from elasticsearch.connection import create_ssl_context
    from elasticsearch.helpers import scan
except ImportError:
    # Only used when running the intention
    pass

from poolsched.models import Intention, Job, ArchivedIntention
from .. import utils

ELASTIC_URL = 'https://{}:{}'.format(settings.ES_IN_HOST, settings.ES_IN_PORT)

CSV_COLUMNS = ['hash', 'repo_name', 'author_uuid', 'author_domain', 'author_date', 'utc_author', 'tz',
               'commit_date', 'utc_commit', 'committer_domain', 'files', 'lines_added', 'lines_removed']

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()


class GitCSVFile(models.Model):
    """Represents a CSV file for a project"""
    project = models.ForeignKey('cauldron.Project', on_delete=models.CASCADE, related_name='git_csv_file')
    created = models.DateTimeField(auto_now_add=True)
    location = models.CharField(max_length=150)


class IExportGitCSVManager(models.Manager):
    """Model manager for instances of IExportGitCSV"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IExportGitCSV intentions for a user

        A intention is selectable if:
        * If it's time for the intention
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IExportGitCSV intentions
        """
        intentions = self.filter(user=user,
                                 job=None,
                                 previous=None)
        return intentions.all()[:max]


class IExportGitCSV(Intention):
    """Intention to export Git data from a project as CSV"""
    objects = IExportGitCSVManager()

    project = models.ForeignKey('cauldron.Project', on_delete=models.CASCADE, related_name='iexport_git_csv')

    class Meta:
        db_table = 'poolsched_export_git_csv'
        verbose_name_plural = "Export Git CSV Intentions"

    @property
    def process_name(self):
        return 'Export Git CSV'

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """
        # intentions with job and no worker.
        intention = cls.objects\
            .select_related('job')\
            .exclude(job=None).filter(job__worker=None)\
            .first()
        if intention:
            return intention.update_job_worker(worker)
        return None

    def running_job(self):
        """Find a job that would satisfy this intention

        If a not done job is found, which would satisfy intention,
        the intention is assigned to that job, which is returned.
        The user token is assigned to it, too.

        :return:          Job object, if it was found, or None, if not
        """
        candidates = IExportGitCSV.objects.filter(project=self.project,
                                                  job__isnull=False)
        try:
            # Find intention with job for the same repo, assign job to self
            self.job = candidates[0].job
            self.save()
        except IndexError:
            # No intention with a job for the same repo found
            return None
        return self.job

    def _export_git_csv(self):
        logger.info('Creating Elasticsearch Object')
        jwt_key = utils.get_jwt_key(f"Project {self.project.id}", self.project.projectrole.backend_role)
        context = create_ssl_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        elastic = Elasticsearch(hosts=[settings.ES_IN_HOST], scheme='https', port=settings.ES_IN_PORT,
                                headers={"Authorization": f"Bearer {jwt_key}"}, ssl_context=context, timeout=5)

        result = scan(elastic,
                      query={"query": {"match_all": {}}},
                      index='git')
        created = datetime.datetime.now()
        location = f"csv/git/project-{self.project.id}-{created.strftime('%Y%m%dT%H%M%S')}.csv"
        file_path = os.path.join(settings.STATIC_FILES_DIR, location)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=CSV_COLUMNS, extrasaction='ignore')
            writer.writeheader()
            for data in result:
                try:
                    writer.writerow(data['_source'])
                except Exception as e:
                    logger.error(f"Error writing row: {e}")
        GitCSVFile.objects.create(project=self.project, created=created, location=location)

    def run(self, job):
        """Run the code to fulfill this intention

        :param job: job to be run
        """

        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            logger.info(f"Exporting Git CSV data")
            self._export_git_csv()
            logger.info(f"Finished without errors")
            return True
        except Exception as e:
            logger.error(f"Error exporting data: {str(e)}")
            raise Job.StopException
        finally:
            global_logger.removeHandler(handler)

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        IExportGitCSVArchived.objects.create(user=self.user,
                                             created=self.created,
                                             status=status,
                                             arch_job=arch_job,
                                             project=self.project)
        self.delete()


class IExportGitCSVArchived(ArchivedIntention):
    project = models.ForeignKey('cauldron.Project', null=True, on_delete=models.SET_NULL)

    @property
    def process_name(self):
        return 'Export Git CSV archived'

    class Meta:
        db_table = 'poolsched_export_git_csv_archived'
        verbose_name_plural = "Export Git CSV Intentions Archived"
