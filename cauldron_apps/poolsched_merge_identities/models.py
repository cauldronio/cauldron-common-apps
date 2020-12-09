import logging
import datetime

from django.db import models, transaction
from django.utils.timezone import now

from poolsched.models import Intention, Job, ArchivedIntention
from .mordred import SHMergeIdentities

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()


class MergeIdentitiesManager(models.Manager):
    """Model manager for instances of IMergeIdentities"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IMergeIdentities intentions for a user

        A intention is selectable if:
        * If it's time for the intention
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: (IGNORED)
        :param max:  maximum number of intentions to return
        :returns:    list of IMergeIdentities intentions
        """
        # Don't select if exists an intention running
        if self.filter(job__isnull=False, job__worker__isnull=False):
            return []
        intentions = self.filter(previous=None,
                                 job=None,
                                 scheduled__lte=now())
        return intentions.all()[:max]


class IMergeIdentities(Intention):
    """Intention to merge indices authors with SortingHat data"""
    objects = MergeIdentitiesManager()

    # Time at which this intentions should run
    scheduled = models.DateTimeField()

    class Meta:
        db_table = 'poolsched_merge_identities'
        verbose_name_plural = "Merge Identities"

    @property
    def process_name(self):
        return 'Merge Identities'

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """

        # intentions with job and no worker.
        # If it has a job is because now > scheduled date
        intention = cls.objects\
            .select_related('job')\
            .exclude(job=None).filter(job__worker=None)\
            .first()
        if intention:
            return intention.update_job_worker(worker)
        return None

    def running_job(self):
        """Find a Job for this intention.
        In this case there shouldn't be any other intention
        """
        return None

    def run(self, job):
        """Run the code to fulfill this intention

        :param job: job to be run
        """

        # Schedule next merge identities
        next_merge = now() + datetime.timedelta(hours=1)
        logger.info(f"Schedule next merge identities for at {next_merge}")
        IMergeIdentities.objects.create(user=self.user, scheduled=next_merge)

        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            logger.info(f"Running Merge identities")
            runner = SHMergeIdentities()
            runner.run()
            logger.info(f"Finished without errors")
            return True
        except Exception as e:
            logger.error(f"Error running Merge identities: {str(e)}")
            raise Job.StopException
        finally:
            global_logger.removeHandler(handler)

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        IMergeIdentitiesArchived.objects.create(user=self.user,
                                                created=self.created,
                                                status=status,
                                                arch_job=arch_job,
                                                scheduled=self.scheduled)
        self.delete()


class IMergeIdentitiesArchived(ArchivedIntention):
    scheduled = models.DateTimeField()

    @property
    def process_name(self):
        return 'Merge Identities Archived'

    class Meta:
        db_table = 'poolsched_merge_identities_archived'
        verbose_name_plural = "Merge Identities Archived"
