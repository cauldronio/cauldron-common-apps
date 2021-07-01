import logging
import ssl

from django.conf import settings
from django.db import models, transaction
from elasticsearch import Elasticsearch, ElasticsearchException
from elasticsearch.connection import create_ssl_context
from elasticsearch_dsl import Search, Q

from poolsched.models import Intention, ArchivedIntention, Job
from .base import GLRepo
from .iraw import IGLRaw

from ..mordred import GitLabEnrich


logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_gl'


class IEnrichedManager(models.Manager):
    """Model manager for IGLEnrich"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IGLEnrich intentions for a user

        A intention is selectable if:
        * no job is still associated with it
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IGLRaw intentions
        """

        intentions = self.filter(previous=None,
                                 user=user,
                                 job=None)
        return intentions.all()[:max]


class IGLEnrich(Intention):
    """Intention for producing enriched indexes for GitLab repos"""

    # GLRepo to analyze
    repo = models.ForeignKey(GLRepo, on_delete=models.PROTECT)

    class Meta:
        db_table = TABLE_PREFIX + 'ienriched'
        verbose_name_plural = "Intentions GLEnrich"
    objects = IEnrichedManager()

    @property
    def process_name(self):
        return "Gitlab data enrichment"

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting.
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """

        intention = IGLEnrich.objects\
            .select_related('job')\
            .exclude(job=None).filter(job__worker=None)\
            .first()
        if intention:
            return intention.update_job_worker(worker)
        return None

    def create_previous(self):
        """Create all needed previous intentions"""

        raw_intention, _ = IGLRaw.objects.get_or_create(repo=self.repo,
                                                        user=self.user)
        self.previous.add(raw_intention)
        return [raw_intention]

    def running_job(self):
        """Find a Job that satisfies this intention

        If a not done job is found, the intention is assigned
        and the job is returned.

        :return: Job object, if it was found, or None, if not
        """

        candidates = self.repo.iglenrich_set.filter(job__isnull=False)
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
            s = Search(using=elastic, index='gitlab_issues') \
                .filter(Q('term', origin=self.repo.gitlabrepository.datasource_url)) \
                .extra(size=0, track_total_hits=True)
            s.aggs.bucket('authors', 'cardinality', field='author_uuid')

            response = s.execute()
            if response is not None and response.success():
                issues_submitters = response.aggregations.authors.value or 0
                issues = response.hits.total['value'] or 0
            else:
                issues_submitters = 0
                issues = 0

            metrics = self.repo.gitlabrepository.metrics
            if metrics:
                metrics.issues = issues
                metrics.issues_submitters = issues_submitters
                metrics.save()
        except ElasticsearchException as e:
            logger.warning(e)

        try:
            s = Search(using=elastic, index='gitlab_mrs') \
                .filter(Q('term', origin=self.repo.gitlabrepository.datasource_url)) \
                .extra(size=0, track_total_hits=True)
            s.aggs.bucket('authors', 'cardinality', field='author_uuid')

            response = s.execute()
            if response is not None and response.success():
                reviews_submitters = response.aggregations.authors.value or 0
                reviews = response.hits.total['value'] or 0
            else:
                reviews_submitters = 0
                reviews = 0

            metrics = self.repo.gitlabrepository.metrics
            if metrics:
                metrics.reviews = reviews
                metrics.reviews_submitters = reviews_submitters
                metrics.save()
        except ElasticsearchException as e:
            logger.warning(e)

    def run(self, job):
        """Run the code to fulfill this intention

        :return:
        """
        logger.info(f"Running GitLabEnrich intention: {self.repo.owner}/{self.repo.repo}")
        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            runner = GitLabEnrich(url=self.repo.url, endpoint=self.repo.instance.endpoint)
            output = runner.run()
            self.update_db_metrics()
            self.repo.gitlabrepository.update_last_refresh()
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
        IGLEnrichArchived.objects.create(user=self.user,
                                         repo=self.repo,
                                         created=self.created,
                                         status=status,
                                         arch_job=arch_job)
        self.delete()


class IGLEnrichArchived(ArchivedIntention):
    """Archived GitLab Enrich intention"""
    repo = models.ForeignKey(GLRepo, on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = "Archived GitLabEnrich"

    @property
    def process_name(self):
        return "Gitlab data enrichment"
