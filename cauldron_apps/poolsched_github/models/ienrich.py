import logging
import ssl

from django.db import models, transaction
from django.conf import settings
from elasticsearch_dsl import Search, Q

from poolsched.models import Intention, ArchivedIntention, Job

from elasticsearch import Elasticsearch, ElasticsearchException
from elasticsearch.connection import create_ssl_context

from ..mordred import GitHubEnrich
from .base import GHRepo
from .iraw import IGHRaw

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_gh'


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

    def update_db_metrics(self):
        context = create_ssl_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        elastic = Elasticsearch(hosts=[settings.ES_IN_HOST], scheme='https', port=settings.ES_IN_PORT,
                                http_auth=("admin", settings.ES_ADMIN_PASSWORD),
                                ssl_context=context, timeout=5)
        try:
            s = Search(using=elastic, index='github') \
                .filter(Q('match', pull_request=False)) \
                .filter(Q('term', origin=self.repo.githubrepository.datasource_url)) \
                .extra(size=0, track_total_hits=True)
            s.aggs.bucket('authors', 'cardinality', field='author_uuid')

            response = s.execute()
            if response is not None and response.success():
                issues_submitters = response.aggregations.authors.value or 0
                issues = response.hits.total['value'] or 0
            else:
                issues_submitters = 0
                issues = 0

            metrics = self.repo.githubrepository.metrics
            if metrics:
                metrics.issues = issues
                metrics.issues_submitters = issues_submitters
                metrics.save()
        except ElasticsearchException as e:
            logger.warning(e)

        try:
            s = Search(using=elastic, index='github') \
                .filter(Q('match', pull_request=True)) \
                .filter(Q('term', origin=self.repo.githubrepository.datasource_url)) \
                .extra(size=0, track_total_hits=True)
            s.aggs.bucket('authors', 'cardinality', field='author_uuid')

            response = s.execute()
            if response is not None and response.success():
                reviews_submitters = response.aggregations.authors.value or 0
                reviews = response.hits.total['value'] or 0
            else:
                reviews_submitters = 0
                reviews = 0

            metrics = self.repo.githubrepository.metrics
            if metrics:
                metrics.reviews = reviews
                metrics.reviews_submitters = reviews_submitters
                metrics.save()
        except ElasticsearchException as e:
            logger.warning(e)

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
            self.update_db_metrics()
            self.repo.githubrepository.update_last_refresh()
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


class IGHEnrichArchived(ArchivedIntention):
    """Archived GitHub Enrich intention"""
    repo = models.ForeignKey(GHRepo, on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = "Archived GitHubEnrich"

    @property
    def process_name(self):
        return "GitHub data enrichment"
