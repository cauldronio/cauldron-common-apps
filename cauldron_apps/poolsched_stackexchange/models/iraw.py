import logging
import datetime

from django.db import models, transaction
from django.db.models import Count
from django.utils.timezone import now

from poolsched.models import Intention, Job, ArchivedIntention
from .base import StackExchangeToken, StackExchangeQuestionTag
from ..mordred import StackExchangeRaw

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_stackexchange'


class IStackExchangeRawManager(models.Manager):
    """Model manager for instances of IStackExchangeRaw"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IStackExchangeRaw intentions for a user

        A intention is selectable if:
        * it's time for the intention
        * its user has a usable token
        * no job is still associated with it
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IStackExchangeRaw intentions
        """
        token_available = user.stackexchangetokens.annotate(num_jobs=Count('jobs')) \
            .filter(num_jobs__lt=StackExchangeToken.MAX_JOBS_TOKEN) \
            .filter(reset__lt=now()) \
            .exists()
        if not token_available:
            logger.debug('No selectable intentions for this user (no token available)')
            return []
        intentions = self.filter(user=user,
                                 job=None,
                                 previous=None)
        return intentions.all()[:max]


class IStackExchangeRaw(Intention):
    """Intention for producing raw indexes for StackExchange sites and tags"""
    objects = IStackExchangeRawManager()

    # Tag and site to analyze
    question_tag = models.ForeignKey(StackExchangeQuestionTag, on_delete=models.PROTECT)

    class Meta:
        db_table = TABLE_PREFIX + 'iraw'
        verbose_name_plural = 'Intentions StackExchangeRaw'

    def __str__(self):
        return f'QuestionTag({self.question_tag})|User({self.user})|Prev({self.previous})|Job({self.job}))'

    @property
    def process_name(self):
        return f'IStackExchangeRaw gathering'

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
            .exclude(job=None).filter(job__worker=None).filter(job__stackexchangetoken__reset__lt=now())\
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
        candidates = self.question_tag.istackexchangeraw_set.filter(job__isnull=False)
        try:
            # Find intention with job for the same repo, assign job to self
            self.job = candidates[0].job
            self.save()
        except IndexError:
            # No intention with a job for the same repo found
            return None

        # Get tokens for the user, and assign them to job
        tokens = StackExchangeToken.objects.filter(user=self.user)
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
        tokens = self.user.stackexchangetokens\
            .annotate(num_jobs=Count('jobs'))\
            .filter(num_jobs__lt=StackExchangeToken.MAX_JOBS_TOKEN)
        # Only create the job if there is at least one token
        if tokens:
            job = super().create_job(worker)
            self.refresh_from_db()
            if self.job:
                self.job.stackexchangetokens.add(*tokens)
            return job
        return None

    def run(self, job):
        """Run the code to fulfill this intention

        :param job: job to be run
        """
        token = job.stackexchangetokens.filter(reset__lt=now()).first()
        logger.info(f"Running StackExchange intention: {self.question_tag.site}/{self.question_tag.tagged}, token: {token}")
        if not token:
            logger.error(f'Token not found for intention {self}')
            raise Job.StopException
        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            runner = StackExchangeRaw(url=self.question_tag.url, token=token.token, api_key=token.api_key)
            output = runner.run()
        except Exception as e:
            logger.error(f"Error running IStackExchangeRaw: {str(e)}")
            raise Job.StopException
        finally:
            global_logger.removeHandler(handler)

        if output == 1:
            logger.error(f"Error running IStackExchangeRaw intention {self}")
            raise Job.StopException
        if output:
            token.reset = now() + datetime.timedelta(minutes=output)
            token.save()
            return False
        return True

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        IStackExchangeRawArchived.objects.create(user=self.user,
                                                 question_tag=self.question_tag,
                                                 created=self.created,
                                                 status=status,
                                                 arch_job=arch_job)
        self.delete()


class IStackExchangeRawArchived(ArchivedIntention):
    """Archived StackExchanged Raw Intention"""
    question_tag = models.ForeignKey(StackExchangeQuestionTag, on_delete=models.PROTECT)

    @property
    def process_name(self):
        return 'Archived StackExchangeRaw'

    class Meta:
        db_table = TABLE_PREFIX + 'iraw_archived'
        verbose_name_plural = 'Archived StackExchangeRaw'
