import logging

from django.db import models, transaction

from poolsched.models import Intention, ArchivedIntention, Job
from .base import MeetupRepo
from .iraw import IMeetupRaw
from ..mordred import MeetupEnrich

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_meetup'


class IEnrichedManager(models.Manager):
    """Model manager for IMeetupEnrich"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IMeetupEnrich intentions for a user

        A intention is selectable if:
        * no job is still associated with it
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IMeetupRaw intentions
        """

        intentions = self.filter(user=user,
                                 job=None,
                                 previous=None)
        return intentions.all()[:max]


class IMeetupEnrich(Intention):
    """Intention for producing enriched indexes for Meetup repos"""
    # MeetupRepo to analyze
    repo = models.ForeignKey(MeetupRepo, on_delete=models.PROTECT)

    class Meta:
        db_table = TABLE_PREFIX + 'ienriched'
        verbose_name_plural = "Intentions MeetEnrich"
    objects = IEnrichedManager()

    def __str__(self):
        return f'Repo({self.repo})|User({self.user})|Prev({self.previous})|Job({self.job})'

    @property
    def process_name(self):
        return "Meetup data enrichment"

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting.
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """

        intention = IMeetupEnrich.objects\
            .select_related('job')\
            .exclude(job=None).filter(job__worker=None)\
            .first()
        if intention:
            return intention.update_job_worker(worker)
        return None

    def create_previous(self):
        """Create all needed previous intentions"""
        raw_intention, _ = IMeetupRaw.objects.get_or_create(repo=self.repo,
                                                            user=self.user)
        self.previous.add(raw_intention)
        return [raw_intention]

    def running_job(self):
        """Find a Job that satisfies this intention

        If a not done job is found, the intention is assigned
        and the job is returned.

        :return: Job object, if it was found, or None, if not
        """

        candidates = self.repo.imeetupenrich_set.filter(job__isnull=False)
        try:
            # Find intention with job for the same repo, assign job to self
            self.job = candidates[0].job
            self.save()
        except IndexError:
            # No intention with a job for the same repo found
            return None
        return self.job

    def run(self, job):
        """Run the code to fulfill this intention
        Returns true if completed

         :param job: job to be run
        """
        logger.info(f"Running MeetupEnrich intention: {self.repo.repo}")
        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            runner = MeetupEnrich(url=self.repo.repo)
            output = runner.run()
        except Exception as e:
            logger.error(f"Error: {e}")
            raise Job.StopException
        finally:
            global_logger.removeHandler(handler)
        if output:
            raise Job.StopException
        return True

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        IMeetupEnrichArchived.objects.create(user=self.user,
                                             repo=self.repo,
                                             created=self.created,
                                             status=status,
                                             arch_job=arch_job)
        self.delete()


class IMeetupEnrichArchived(ArchivedIntention):
    """Archived Meetup Enrich intention"""
    repo = models.ForeignKey(MeetupRepo, on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = "Archived MeetupEnrich"

    @property
    def process_name(self):
        return "Meetup data enrichment"
