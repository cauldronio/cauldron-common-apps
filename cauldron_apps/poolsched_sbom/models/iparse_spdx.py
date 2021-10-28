import logging
import os.path

from django.db import models, transaction
from django.conf import settings

from poolsched.models import Intention, Job, ArchivedIntention
from .base import SPDXUserFile
from .. import parse_spdx

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()


class IParseSPDXManager(models.Manager):
    """Model manager for instances of IParseSPDX"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IParseSPDX intentions for a user

        A intention is selectable if:
        * no job is still associated with it

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IParseSPDX intentions
        """
        intentions = self.filter(user=user,
                                 job=None,
                                 previous=None)
        return intentions.all()[:max]


class IParseSPDX(Intention):
    """Intention to parse a SBOM document and return the list of repositories"""
    objects = IParseSPDXManager()

    spdx_file = models.ForeignKey(SPDXUserFile, on_delete=models.CASCADE)

    class Meta:
        db_table = 'poolsched_sbom_iparse'
        verbose_name_plural = 'Intentions ParseSPDX'

    @property
    def process_name(self):
        return 'SPDX file parser'

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """

        intention = cls.objects\
            .select_related('job')\
            .exclude(job=None).filter(job__worker=None)\
            .first()
        if intention:
            return intention.update_job_worker(worker)
        return None

    def running_job(self):
        # No intention with a job for the same file will be found
        return None

    def parse_file(self, filename):
        parse_spdx.parse_file(filename)

    def run(self, job):
        """Run the code to fulfill this intention

        :param job: job to be run
        """
        logger.info(f"Running ParseSPDX intention: {self.id}")
        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            logger.info(f"Running IParseSPDX")
            location = os.path.join(settings.SPDX_FILES_PATH, self.spdx_file.location)
            dependencies = parse_spdx.source_repositories(location)
            self.spdx_file.result = {"results": dependencies, "error": None}
            self.spdx_file.save()
            logger.info(dependencies)
            logger.info(f"Finished without errors")
            return True
        except Exception as e:
            self.spdx_file.result = {"results": None, "error": str(e)}
            self.spdx_file.save()
            logger.error(f"Error running IParseSPDX: {str(e)}")
            raise Job.StopException
        finally:
            global_logger.removeHandler(handler)

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        IParseSPDXArchived.objects.create(user=self.user,
                                          created=self.created,
                                          status=status,
                                          arch_job=arch_job,
                                          user_file=self.spdx_file)
        self.delete()


class IParseSPDXArchived(ArchivedIntention):
    """Archived parse SPDX file"""
    user_file = models.ForeignKey(SPDXUserFile, on_delete=models.PROTECT)

    @property
    def process_name(self):
        return 'Parse SPDX'

    class Meta:
        db_table = 'poolsched_parse_SPDX_archived'
        verbose_name_plural = "SPDX parsers"
