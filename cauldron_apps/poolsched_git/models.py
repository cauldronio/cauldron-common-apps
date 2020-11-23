import logging

from django.db import models, transaction
from django.utils.timezone import now

from poolsched.models import Job, Intention, ArchivedIntention

from .mordred import GitEnrich, GitRaw

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_git'


class GitRepo(models.Model):
    """Git repository"""

    url = models.CharField(max_length=255, unique=True)

    # When the repo was created in the scheduler
    created = models.DateTimeField(default=now, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'repo'
        verbose_name_plural = "Repositories Git"


class IRawManager(models.Manager):
    """Model manager for IGitRaw"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IGitRaw intentions for a user

        A intention is selectable if:
        * it's status is ready
        * no job is still associated with it
        It's not important if there is other job for the same url,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IGitRaw intentions
        """

        intentions = self.filter(user=user,
                                 job=None)
        return intentions.all()[:max]


class IGitRaw(Intention):
    """Intention for producing raw indexes for Git repos"""

    # GitRepo to analyze
    repo = models.ForeignKey(GitRepo, on_delete=models.PROTECT)

    class Meta:
        db_table = TABLE_PREFIX + 'iraw'
        verbose_name_plural = "Intentions GitRaw"
    objects = IRawManager()

    @property
    def process_name(self):
        return "Git data gathering"

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """

        intention = IGitRaw.objects\
            .select_related('job')\
            .exclude(job=None).filter(job__worker=None)\
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

        :return:          Job object, if it was found, or None, if not
        """

        candidates = self.repo.igitraw_set.filter(job__isnull=False)
        try:
            # Find intention with job for the same repo, assign job to self
            self.job = candidates[0].job
        except IndexError:
            # No intention with a job for the same repo found
            return None
        self.save()
        return self.job

    def run(self, job):
        """Run the code to fulfill this intention.
        Returns true if completed

        :param job: job to be run
        """
        logger.info(f"Running GitRaw intention: {self.repo.url}")
        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            runner = GitRaw(self.repo.url)
            output = runner.run()
            if output:
                raise Job.StopException
        except Exception as e:
            logger.error(f"Error: {e}")
            raise Job.StopException
        finally:
            global_logger.removeHandler(handler)
        return True

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        IGitRawArchived.objects.create(user=self.user,
                                       repo=self.repo,
                                       created=self.created,
                                       status=status,
                                       arch_job=arch_job)
        self.delete()


class IEnrichedManager(models.Manager):
    """Model manager for IGitEnrich"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IGitEnrich intentions for a user

        A intention is selectable if:
        * it's status is ready
        * no job is still associated with it
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IGitRaw intentions
        """

        intentions = self.filter(user=user,
                                 job=None,
                                 previous=None)
        return intentions.all()[:max]


class IGitEnrich(Intention):
    """Intention for producing enriched indexes for Git repos"""

    # GitRepo to analyze
    repo = models.ForeignKey(GitRepo, on_delete=models.PROTECT)

    class Meta:
        db_table = TABLE_PREFIX + 'ienriched'
        verbose_name_plural = "Intentions GitEnrich"
    objects = IEnrichedManager()

    @property
    def process_name(self):
        return "Git data enrichment"

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting.
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """

        intention = IGitEnrich.objects\
            .select_related('job')\
            .exclude(job=None).filter(job__worker=None)\
            .first()
        if intention:
            return intention.update_job_worker(worker)
        return None

    def create_previous(self):
        """Create all needed previous intentions"""

        raw_intention, _ = IGitRaw.objects.get_or_create(repo=self.repo,
                                                         user=self.user)
        self.previous.add(raw_intention)
        return [raw_intention]

    def running_job(self):
        """Find a Job that satisfies this intention

        If a not done job is found, the intention is assigned
        and the job is returned.

        :return: Job object, if it was found, or None, if not
        """

        candidates = self.repo.igitenrich_set.filter(job__isnull=False)
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
        :return:
        """
        logger.info(f"Running GitEnrich intention: {self.repo.url}")
        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            runner = GitEnrich(self.repo.url)
            output = runner.run()
            if output:
                raise Job.StopException
        except Exception as e:
            logger.error(f"Error: {e}")
            raise Job.StopException
        finally:
            global_logger.removeHandler(handler)
        return True

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        IGitEnrichArchived.objects.create(user=self.user,
                                          repo=self.repo,
                                          created=self.created,
                                          status=status,
                                          arch_job=arch_job)
        self.delete()


class IGitRawArchived(ArchivedIntention):
    repo = models.ForeignKey(GitRepo, on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = "Archived GitRaw"

    @property
    def process_name(self):
        return "Git data gathering"


class IGitEnrichArchived(ArchivedIntention):
    repo = models.ForeignKey(GitRepo, on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = "Archived GitEnrich"

    @property
    def process_name(self):
        return "Git data enrichment"
