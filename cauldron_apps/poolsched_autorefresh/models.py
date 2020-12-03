"""
IAutorefresh is an abstract class for autorefresh in SortingHat.
Each backend extend this class with custom attributes.
It is mandatory that subclasses extend this class and Intention,
if not, intention.cast() won't work
"""

import logging
import datetime

from django.db import models, transaction
from django.utils.timezone import now

from poolsched.models import Intention, Job, ArchivedIntention
from .mordred import SHAutoRefresh

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()


class AutoRefreshManager(models.Manager):
    """Model manager for instances of IAutorefresh"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable ISHRefresh intentions for a user

        A intention is selectable if:
        * If it's time for the intention
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: (IGNORED)
        :param max:  maximum number of intentions to return
        :returns:    list of IGHRaw intentions
        """
        # Don't select if exists an intention running
        if self.filter(job__isnull=False, job__worker__isnull=False):
            return []
        intentions = self.filter(previous=None,
                                 job=None,
                                 scheduled__lte=now())
        return intentions.all()[:max]


class IAutorefresh(Intention):
    """Intention to refresh indices with SortingHat data"""

    # Time at which previous intention run
    last_autorefresh = models.DateTimeField(null=True)
    # Time at which this intentions should run
    scheduled = models.DateTimeField()

    class Meta:
        abstract = True

    @property
    def process_name(self):
        raise NotImplementedError

    @property
    def backend(self):
        """Returns the name of the backend"""
        raise NotImplementedError

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

    def _run_backend(self, job):
        """Run auto refresh for a backend.
        Return whether it finishes OK (True) or BAD (False)
        """
        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            logger.info(f"Running Autorefresh for {self.backend} from {self.last_autorefresh} to {now()}")
            runner = SHAutoRefresh(self.backend, self.last_autorefresh)
            runner.run()
        except Exception as e:
            logger.error(f"Error running Autorefresh for {self.backend}: {str(e)}")
            return False
        finally:
            global_logger.removeHandler(handler)
        return True

    def run(self, job):
        """Run the code to fulfill this intention

        :param job: job to be run
        """
        # TODO: Synchronize enrich tasks if needed

        # Schedule next autorefresh with current last_autorefresh in case this one fails
        autorefresh_start = now()
        next_autorefresh = autorefresh_start + datetime.timedelta(hours=1)
        logger.info(f"Schedule next autorefresh for {self.backend} at {next_autorefresh}")
        sched_autorefresh = self.__class__.objects.create(user=self.user,
                                                          scheduled=next_autorefresh,
                                                          last_autorefresh=self.last_autorefresh)

        logger.info(f"Running Autorefresh intention")
        success = self._run_backend(job)
        if success:
            # Update next autorefresh dates
            sched_autorefresh.scheduled = now() + datetime.timedelta(hours=1)
            sched_autorefresh.last_autorefresh = autorefresh_start
            sched_autorefresh.save()
            logger.info(f"Reschedule autorefresh for {self.backend} at {sched_autorefresh.scheduled}")
            return True
        else:
            # Intention already scheduled, run again later with same last_autorefresh
            logger.error(f"Error running AutorefreshSH intention {self}")
            raise Job.StopException

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        self.__class__._archived_model().objects.create(user=self.user,
                                                        created=self.created,
                                                        status=status,
                                                        arch_job=arch_job,
                                                        scheduled=self.scheduled,
                                                        last_autorefresh=self.last_autorefresh)
        self.delete()

    @classmethod
    def _archived_model(cls):
        """Implement in subclasses.
        Return the model in which this intention should be archived"""
        raise NotImplementedError


class IAutorefreshArchived(ArchivedIntention):
    last_autorefresh = models.DateTimeField(null=True)
    scheduled = models.DateTimeField()

    class Meta:
        abstract = True

    @property
    def process_name(self):
        raise NotImplementedError
