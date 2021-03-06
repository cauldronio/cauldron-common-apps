import datetime
import logging

from django.db import models, transaction
from django.db.models import Count
from django.utils.timezone import now

from poolsched.models import Intention, ArchivedIntention, Job
from .base import MeetupToken, MeetupRepo
from ..mordred import MeetupRaw

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_meetup'


class IRawManager(models.Manager):
    """Model manager for IMeetupRaw"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IMeetRaw intentions for a user

        A intention is selectable if:
        * its user has a usable token
        * no job is still associated with it
        * (future) in fact, either its user has a usable token,
          or there is other (public) token available
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IMeetRaw intentions
        """
        token_available = user.meetuptokens.annotate(num_jobs=Count('jobs'))\
            .filter(num_jobs__lt=MeetupToken.MAX_JOBS_TOKEN)\
            .filter(reset__lt=now())\
            .exists()
        if not token_available:
            logger.debug('No selectable intentions for this user (no token available)')
            return []
        intentions = self.filter(previous=None,
                                 user=user,
                                 job=None)
        return intentions.all()[:max]


class IMeetupRaw(Intention):
    """Intention for producing raw indexes for Meetup repos"""

    # MeetupRepo to analyze
    repo = models.ForeignKey(MeetupRepo, on_delete=models.PROTECT)

    class Meta:
        db_table = TABLE_PREFIX + 'iraw'
        verbose_name_plural = "Intentions MeetRaw"
    objects = IRawManager()

    class TokenExhaustedException(Job.StopException):
        """Exception to raise if the Meetup token is exhausted

        Will be raised if the token is exhausted while the data
        for the repo is being retrieved. In this case, likely the
        retrieval was not finished."""

        def __init__(self, token, message="MeetupToken exhausted"):
            """
            Job could not finish because token was exhausted.
            """

            self.message = message
            self.token = token

        def __str__(self):
            return self.message

    def __str__(self):
        return f'Repo({self.repo})|User({self.user})|Prev({self.previous})|Job({self.job}))'

    @property
    def process_name(self):
        return "Meetup data gathering"

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting, and have a token ready.
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """

        intention = IMeetupRaw.objects\
            .select_related('job')\
            .exclude(job=None).filter(job__worker=None).filter(job__meetuptoken__reset__lt=now())\
            .first()
        if intention:
            return intention.update_job_worker(worker)
        return None

    def create_previous(self):
        """Create all needed previous intentions (no previous intention needed)"""
        return []

    def running_job(self):
        """Find a job that would satisfy this intention

        If a not done job is found, which would satisfy intention,
        the intention is assigned to that job, which is returned.
        The user token is assigned to it, too.

        :return:          Job object, if it was found, or None, if not
        """

        candidates = self.repo.imeetupraw_set.filter(job__isnull=False)
        try:
            # Find intention with job for the same repo, assign job to self
            self.job = candidates[0].job
        except IndexError:
            # No intention with a job for the same repo found
            return None
        self.save()
        # Get tokens for the user, and assign them to job
        tokens = MeetupToken.objects.filter(user=self.user)
        token_included = False
        for token in tokens:
            if token.jobs.count() < token.MAX_JOBS_TOKEN:
                token_included = True
                token.jobs.add(self.job)
        if token_included:
            return self.job
        else:
            return None

    def create_job(self, worker):
        """Create a new job for this intention
        Adds the job to the intention, too.

        If the worker didn't create the job, return None

        A IRaW intention cannot run if there are too many jobs
        using available tokens.

        :param worker: Worker willing to create the job.
        :returns:      Job created by the worker, or None
        """
        tokens = self.user.meetuptokens\
            .annotate(num_jobs=Count('jobs'))\
            .filter(num_jobs__lt=MeetupToken.MAX_JOBS_TOKEN)
        # Only create the job if there is at least one token
        if tokens:
            job = super().create_job(worker)
            self.refresh_from_db()
            if self.job:
                self.job.meetuptokens.add(*tokens)
            return job
        return None

    def run(self, job):
        """Run the code to fulfill this intention

        :param job: job to be run
        """
        token = job.meetuptokens.filter(reset__lt=now()).first()
        logger.info(f"Running MeetupRaw intention: {self.repo.repo}, token: {token}")
        if not token:
            logger.error(f'Token not found for intention {self}')
            raise Job.StopException
        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            runner = MeetupRaw(url=self.repo.repo, token=token.token)
            output = runner.run()
        except Exception as e:
            logger.error(f"Error running MeetupRaw intention {str(e)}")
            output = 1
        finally:
            global_logger.removeHandler(handler)

        if output == 1:
            logger.error(f"Error running MeetupRaw intention {self}")
            raise Job.StopException
        if output:
            token.reset = now() + datetime.timedelta(minutes=output)
            token.save()
            return False
        return True

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        IMeetupRawArchived.objects.create(user=self.user,
                                          repo=self.repo,
                                          created=self.created,
                                          status=status,
                                          arch_job=arch_job)
        self.delete()


class IMeetupRawArchived(ArchivedIntention):
    """Archived Meetup Raw intention"""
    repo = models.ForeignKey(MeetupRepo, on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = "Archived MeetupRaw"

    @property
    def process_name(self):
        return "Meetup data gathering"
