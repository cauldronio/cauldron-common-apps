import logging

from django.db import models, transaction

from poolsched.models import Intention, Job, ArchivedIntention
from .iraw import IStackExchangeRaw
from .base import StackExchangeQuestionTag
from ..mordred import StackExchangeEnrich

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_stackexchange'


class IStackExchangeEnrichManager(models.Manager):
    """Model manager for instances of IStackExchangeEnrich"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IStackExchangeEnrich intentions for a user

        A intention is selectable if:
        * If it's time for the intention
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IStackExchangeEnrich intentions
        """
        intentions = self.filter(user=user,
                                 job=None,
                                 previous=None)
        return intentions.all()[:max]


class IStackExchangeEnrich(Intention):
    """Intention to produce enriched indexes for StackExchange questions"""
    objects = IStackExchangeEnrichManager()

    # Tag and site to analyze
    question_tag = models.ForeignKey(StackExchangeQuestionTag, on_delete=models.PROTECT)

    class Meta:
        db_table = TABLE_PREFIX + 'ienriched'
        verbose_name_plural = "Intentions StackExchangeEnrich"

    def __str__(self):
        return f'QuestionTag({self.question_tag})|User({self.user})|Prev({self.previous})|Job({self.job}))'

    @property
    def process_name(self):
        return 'StackExchange data enrichment'

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

    def create_previous(self):
        """Create all needed previous intentions"""
        raw_intention, _ = IStackExchangeRaw.objects.get_or_create(question_tag=self.question_tag,
                                                                   user=self.user)
        self.previous.add(raw_intention)
        return [raw_intention]

    def running_job(self):
        """Find a job that would satisfy this intention

        If a not done job is found, which would satisfy intention,
        the intention is assigned to that job, which is returned.
        The user token is assigned to it, too.

        :return:          Job object, if it was found, or None, if not
        """
        candidates = self.question_tag.istackexchangeenrich_set.filter(job__isnull=False)
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

        :param job: job to be run
        """
        logger.info(f"Running StackExchange intention: {self.question_tag.url}")
        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            runner = StackExchangeEnrich(url=self.question_tag.url)
            output = runner.run()
        except Exception as e:
            logger.error(f"Error running IStackExchangeEnrich: {str(e)}")
            raise Job.StopException
        finally:
            global_logger.removeHandler(handler)
        if output:
            raise Job.StopException
        return True

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        IStackExchangeEnrichArchived.objects.create(user=self.user,
                                                    question_tag=self.question_tag,
                                                    created=self.created,
                                                    status=status,
                                                    arch_job=arch_job)
        self.delete()


class IStackExchangeEnrichArchived(ArchivedIntention):
    """Archived StackExchange Enrich intention"""
    question_tag = models.ForeignKey(StackExchangeQuestionTag, on_delete=models.PROTECT)

    @property
    def process_name(self):
        return 'Archived StackExchangeEnrich'

    class Meta:
        db_table = TABLE_PREFIX + 'ienrich_archived'
        verbose_name_plural = "Archived StackExchangeEnrich"
