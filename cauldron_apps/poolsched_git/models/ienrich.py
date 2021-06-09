import logging
import ssl

from django.conf import settings
from django.db import models, transaction
from elasticsearch import Elasticsearch, ElasticsearchException
from elasticsearch.connection import create_ssl_context
from elasticsearch_dsl import Search, Q

from poolsched.models import Job, Intention, ArchivedIntention
from .base import GitRepo
from .iraw import IGitRaw
from ..mordred import GitEnrich

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_git'


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

    def update_db_metrics(self):
        logger.info("Update total commits in database")
        context = create_ssl_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        elastic = Elasticsearch(hosts=[settings.ES_IN_HOST], scheme='https', port=settings.ES_IN_PORT,
                                http_auth=("admin", settings.ES_ADMIN_PASSWORD),
                                ssl_context=context, timeout=5)
        s = Search(using=elastic, index='git') \
            .filter(~Q('match', files=0)) \
            .filter(Q('term', origin=self.repo.gitrepository.datasource_url)) \
            .extra(size=0)
        s.aggs.bucket('commits', 'cardinality', field='hash')

        try:
            response = s.execute()
        except ElasticsearchException as e:
            logger.warning(e)
            response = None

        if response is not None and response.success():
            value = response.aggregations.commits.value or 0
        else:
            value = 0

        metrics = self.repo.gitrepository.metrics
        if metrics:
            logger.info(f"There are {value} commits")
            metrics.commits = value
            metrics.save()

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
            self.update_db_metrics()
            self.repo.gitrepository.update_last_refresh()
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


class IGitEnrichArchived(ArchivedIntention):
    repo = models.ForeignKey(GitRepo, on_delete=models.PROTECT)

    class Meta:
        verbose_name_plural = "Archived GitEnrich"

    @property
    def process_name(self):
        return "Git data enrichment"
