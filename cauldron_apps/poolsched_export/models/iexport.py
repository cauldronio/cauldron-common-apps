import datetime
import logging
import os

from django.db import models, transaction
from django.conf import settings

from poolsched.models import Intention, Job, ArchivedIntention
from cauldron_apps.cauldron.models.backends import Backends
from .. import backends

ELASTIC_URL = 'https://{}:{}'.format(settings.ES_IN_HOST, settings.ES_IN_PORT)

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()


class ProjectExportFile(models.Model):
    """Represents a compressed CSV file for a project"""
    project = models.ForeignKey('cauldron.Project', on_delete=models.CASCADE, related_name='file_exported')
    created = models.DateTimeField(auto_now_add=True)
    location = models.CharField(max_length=150)
    size = models.IntegerField()
    backend = models.CharField(max_length=2, choices=Backends.choices)


class IExportCSVManager(models.Manager):
    """Model manager for instances of IExportCSV"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IExportCSV intentions for a user

        A intention is selectable if:
        * If it's time for the intention
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IExportCSV intentions
        """
        intentions = self.filter(user=user,
                                 job=None,
                                 previous=None)
        return intentions.all()[:max]


class IExportCSV(Intention):
    """Intention to export data from a project as CSV"""
    objects = IExportCSVManager()

    project = models.ForeignKey('cauldron.Project', on_delete=models.CASCADE, related_name='iexport_csv')
    backend = models.CharField(max_length=2, choices=Backends.choices)

    class Meta:
        db_table = 'poolsched_export_csv'
        verbose_name_plural = "Export CSV Intentions"

    @property
    def process_name(self):
        return 'Export CSV'

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """
        # intentions with job and no worker.
        intention = cls.objects \
            .select_related('job') \
            .exclude(job=None).filter(job__worker=None) \
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
        candidates = IExportCSV.objects.filter(project=self.project,
                                               backend=self.backend,
                                               job__isnull=False)
        try:
            # Find intention with job for the same repo, assign job to self
            self.job = candidates[0].job
            self.save()
        except IndexError:
            # No intention with a job for the same repo found
            return None
        return self.job

    def _remove(self, directory, project_files):
        """Remove a list of ProjectExportFile and it's related files"""
        for project_file in project_files:
            try:
                os.remove(os.path.join(directory, project_file.location))
            except OSError:
                pass
            else:
                logger.info(f"{project_file} removed")
            project_file.delete()

    def run(self, job):
        """Run the code to fulfill this intention

        :param job: job to be run
        """

        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            logger.info(f"Start exporting CSV data")
            klass = backends.backend_export.get(self.backend, None)
            if not klass:
                logger.error(f'Backend not implemented: {self.get_backend_display()}')
                raise Job.StopException(f"Backend not implemented: {self.get_backend_display()}")

            created = datetime.datetime.utcnow()
            if self.backend == Backends.GITLAB:
                filename = f"csv/{self.get_backend_display()}/" \
                           f"project-{self.project.id}-" \
                           f"{self.get_backend_display()}-" \
                           f"{created.strftime('%Y%m%dT%H%M%S')}.tar.gz"
            else:
                filename = f"csv/{self.get_backend_display()}/" \
                           f"project-{self.project.id}-" \
                           f"{self.get_backend_display()}-" \
                           f"{created.strftime('%Y%m%dT%H%M%S')}.csv.gz"
            file_path = os.path.join(settings.STATIC_FILES_DIR, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            export_data = klass(project_role=self.project.projectrole.backend_role,
                                es_host=settings.ES_IN_HOST,
                                es_port=settings.ES_IN_PORT,
                                es_scheme='https')
            export_data.store_csv(file_path=file_path,
                                  compress=True,
                                  sortinghat=settings.SORTINGHAT)
            size = os.path.getsize(file_path)
            obj = ProjectExportFile.objects.create(project=self.project,
                                                   backend=self.backend,
                                                   created=created,
                                                   size=size,
                                                   location=filename)
            logger.info("Removing older files")
            older_files = ProjectExportFile.objects.filter(project=self.project,
                                                           backend=self.backend) \
                                                   .exclude(id=obj.id)
            self._remove(settings.STATIC_FILES_DIR, older_files)
            return True
        except Exception as e:
            logger.exception('Got exception exporting data')
            raise Job.StopException
        finally:
            global_logger.removeHandler(handler)

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        IExportCSVArchived.objects.create(user=self.user,
                                          created=self.created,
                                          status=status,
                                          arch_job=arch_job,
                                          project=self.project,
                                          backend=self.backend)
        self.delete()


class IExportCSVArchived(ArchivedIntention):
    project = models.ForeignKey('cauldron.Project', null=True, on_delete=models.SET_NULL)
    backend = models.CharField(max_length=2, choices=Backends.choices)

    @property
    def process_name(self):
        return 'Export CSV archived'

    class Meta:
        db_table = 'poolsched_export_csv_archived'
        verbose_name_plural = "Export CSV Intentions Archived"
