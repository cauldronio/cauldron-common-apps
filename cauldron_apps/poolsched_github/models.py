import logging
import datetime

from django.db import models, transaction
from django.conf import settings
from django.db.models import Count
from django.utils.timezone import now

from poolsched.models import Intention, ArchivedIntention, Job
from cauldron_apps.poolsched_autorefresh.models import IAutorefresh, IAutorefreshArchived, AutoRefreshManager

from .mordred import GitHubRaw, GitHubEnrich

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_gh'


class GHInstance(models.Model):
    """GHInstance of GitHub, or GitHub Enterprise"""

    name = models.CharField(max_length=40, unique=True)
    endpoint = models.CharField(max_length=200)

    class Meta:
        db_table = TABLE_PREFIX + 'instance'


class GHRepo(models.Model):
    """GitHub repository"""

    # GitHub owner
    owner = models.CharField(max_length=40)
    # GitHub repo
    repo = models.CharField(max_length=100)
    # GitHub instance
    instance = models.ForeignKey(
        GHInstance, on_delete=models.SET_NULL,
        default=None, null=True, blank=True)
    # When the repo was created in the scheduler
    created = models.DateTimeField(default=now, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'repo'
        verbose_name_plural = "Repositories GitHub"
        # The combination (onwer, repo, instance) should be unique
        unique_together = ('owner', 'repo', 'instance')

    @property
    def url(self):
        return f'{self.instance.endpoint}/{self.owner}/{self.repo}'


class GHToken(models.Model):
    """GitHub token"""

    # Maximum number of jobs using a token concurrently
    MAX_JOBS_TOKEN = 3

    # GHToken string
    token = models.CharField(max_length=40)
    # Rate limit remaining, last time it was checked
    # rate = models.IntegerField(default=0)
    # Rate limit reset, last time it was checked
    reset = models.DateTimeField(default=now)
    # Owner of the token
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        default=None, null=True, blank=True,
        related_name='ghtokens',
        related_query_name='ghtoken')
    # Jobs using the token
    jobs = models.ManyToManyField(
        Job,
        related_name='ghtokens',
        related_query_name='ghtoken')
    # TODO: Include instance

    class Meta:
        db_table = TABLE_PREFIX + 'token'
        verbose_name_plural = "Tokens GitHub"

    @property
    def is_ready(self):
        return now() > self.reset


class IRawManager(models.Manager):
    """Model manager for IGitHubRaw"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IGHRaw intentions for a user

        A intention is selectable if:
        * its user has a usable token
        * no job is still associated with it
        * (future) in fact, either its user has a usable token,
          or there is other (public) token avilable
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IGHRaw intentions
        """
        token_available = user.ghtokens.annotate(num_jobs=Count('jobs'))\
            .filter(num_jobs__lt=GHToken.MAX_JOBS_TOKEN)\
            .filter(reset__lt=now())\
            .exists()
        if not token_available:
            logger.debug('No selectable intentions for this user (no token available)')
            return []
        intentions = self.filter(previous=None,
                                 user=user,
                                 job=None)
        return intentions.all()[:max]


class IGHRaw(Intention):
    """Intention for producing raw indexes for GitHub repos"""

    # GHRepo to analyze
    repo = models.ForeignKey(GHRepo, on_delete=models.PROTECT)

    class Meta:
        db_table = TABLE_PREFIX + 'iraw'
        verbose_name_plural = "Intentions GHRaw"
    objects = IRawManager()

    class TokenExhaustedException(Job.StopException):
        """Exception to raise if the GitHub token is exhausted

        Will be raised if the token is exhausted while the data
        for the repo is being retrieved. In this case, likely the
        retrieval was not finished."""

        def __init__(self, token, message="GHToken exhausted"):
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
        return "GitHub data gathering"

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting, and have a token ready.
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """

        intention = IGHRaw.objects\
            .select_related('job')\
            .exclude(job=None).filter(job__worker=None).filter(job__ghtoken__reset__lt=now())\
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

        candidates = self.repo.ighraw_set.filter(job__isnull=False)
        try:
            # Find intention with job for the same repo, assign job to self
            self.job = candidates[0].job
        except IndexError:
            # No intention with a job for the same repo found
            return None
        self.save()
        # Get tokens for the user, and assign them to job
        tokens = GHToken.objects.filter(user=self.user)
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
        tokens = self.user.ghtokens\
            .annotate(num_jobs=Count('jobs'))\
            .filter(num_jobs__lt=GHToken.MAX_JOBS_TOKEN)
        # Only create the job if there is at least one token
        if tokens:
            job = super().create_job(worker)
            self.refresh_from_db()
            if self.job:
                self.job.ghtokens.add(*tokens)
            return job
        return None

    def run(self, job):
        """Run the code to fulfill this intention

        :param job: job to be run
        """
        token = job.ghtokens.filter(reset__lt=now()).first()
        logger.info(f"Running GitHubRaw intention: {self.repo.owner}/{self.repo.repo}, token: {token}")
        if not token:
            logger.error(f'Token not found for intention {self}')
            raise Job.StopException
        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            runner = GitHubRaw(url=self.repo.url, token=token.token)
            output = runner.run()
        except Exception as e:
            logger.error(f"Error running GitHubRaw intention {str(e)}")
            output = 1
        finally:
            global_logger.removeHandler(handler)

        if output == 1:
            logger.error(f"Error running GitHubRaw intention {self}")
            raise Job.StopException
        if output:
            token.reset = now() + datetime.timedelta(minutes=output)
            token.save()
            return False
        return True

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        IGHRawArchived.objects.create(user=self.user,
                                      repo=self.repo,
                                      created=self.created,
                                      status=status,
                                      arch_job=arch_job)
        self.delete()


class IEnrichedManager(models.Manager):
    """Model manager for IGHEnrich"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IGHEnrich intentions for a user

        A intention is selectable if:
        * no job is still associated with it
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IGHRaw intentions
        """

        intentions = self.filter(user=user,
                                 job=None,
                                 previous=None)
        return intentions.all()[:max]


class IGHEnrich(Intention):
    """Intention for producing enriched indexes for GitHub repos"""
    # GHRepo to analyze
    repo = models.ForeignKey(GHRepo, on_delete=models.PROTECT)

    class Meta:
        db_table = TABLE_PREFIX + 'ienriched'
        verbose_name_plural = "Intentions GHEnrich"
    objects = IEnrichedManager()

    def __str__(self):
        return f'Repo({self.repo})|User({self.user})|Prev({self.previous})|Job({self.job})'

    @property
    def process_name(self):
        return "GitHub data enrichment"

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting.
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """

        intention = IGHEnrich.objects\
            .select_related('job')\
            .exclude(job=None).filter(job__worker=None)\
            .first()
        if intention:
            return intention.update_job_worker(worker)
        return None

    def create_previous(self):
        """Create all needed previous intentions"""
        raw_intention, _ = IGHRaw.objects.get_or_create(repo=self.repo,
                                                        user=self.user)
        self.previous.add(raw_intention)
        return [raw_intention]

    def running_job(self):
        """Find a Job that satisfies this intention

        If a not done job is found, the intention is assigned
        and the job is returned.

        :return: Job object, if it was found, or None, if not
        """

        candidates = self.repo.ighenrich_set.filter(job__isnull=False)
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
        logger.info(f"Running GitHubEnrich intention: {self.repo.owner}/{self.repo.repo}")
        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            runner = GitHubEnrich(url=self.repo.url)
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
        IGHEnrichArchived.objects.create(user=self.user,
                                         repo=self.repo,
                                         created=self.created,
                                         status=status,
                                         arch_job=arch_job)
        self.delete()


class IGHRawArchived(ArchivedIntention):
    """Archived GitHub Raw intention"""
    repo = models.ForeignKey(GHRepo, on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = "Archived GitHubRaw"

    @property
    def process_name(self):
        return "GitHub data gathering"


class IGHEnrichArchived(ArchivedIntention):
    """Archived GitHub Enrich intention"""
    repo = models.ForeignKey(GHRepo, on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = "Archived GitHubEnrich"

    @property
    def process_name(self):
        return "GitHub data enrichment"


class IGHIssueAutoRefresh(IAutorefresh, Intention):
    objects = AutoRefreshManager()

    @property
    def backend(self):
        return 'github:issue'

    @property
    def process_name(self):
        return 'GH Issue Autorefresh'

    @classmethod
    def _archived_model(cls):
        return IGHIssueAutoRefreshArchived

    class Meta:
        db_table = TABLE_PREFIX + '_issue_autorefresh'
        verbose_name_plural = "GH Issue Autorefresh"


class IGHIssueAutoRefreshArchived(IAutorefreshArchived):
    @property
    def process_name(self):
        return 'GH Issue Autorefresh Archived'

    class Meta:
        db_table = TABLE_PREFIX + '_issue_autorefresh_archived'
        verbose_name_plural = "GH Issue Autorefresh Archived"


class IGHRepoAutoRefresh(IAutorefresh, Intention):
    objects = AutoRefreshManager()

    @property
    def backend(self):
        return 'github:repo'

    @property
    def process_name(self):
        return 'GH Repo Autorefresh'

    @classmethod
    def _archived_model(cls):
        return IGHRepoAutoRefreshArchived

    class Meta:
        db_table = TABLE_PREFIX + '_repo_autorefresh'
        verbose_name_plural = "GH Repo Autorefresh"


class IGHRepoAutoRefreshArchived(IAutorefreshArchived):
    @property
    def process_name(self):
        return 'GH Repo Autorefresh Archived'

    class Meta:
        db_table = TABLE_PREFIX + '_repo_autorefresh_archived'
        verbose_name_plural = "GH Repo Autorefresh Archived"


class IGH2IssueAutoRefresh(IAutorefresh, Intention):
    objects = AutoRefreshManager()

    @property
    def backend(self):
        return 'github2:issue'

    @property
    def process_name(self):
        return 'GH2 Issue Autorefresh'

    @classmethod
    def _archived_model(cls):
        return IGH2IssueAutoRefreshArchived

    class Meta:
        db_table = TABLE_PREFIX + '2_issue_autorefresh'
        verbose_name_plural = "GH2 Issue Autorefresh"


class IGH2IssueAutoRefreshArchived(IAutorefreshArchived):
    @property
    def process_name(self):
        return 'GH2 Issue Autorefresh Archived'

    class Meta:
        db_table = TABLE_PREFIX + '2_issue_autorefresh_archived'
        verbose_name_plural = "GH2 Issue Autorefresh Archived"
