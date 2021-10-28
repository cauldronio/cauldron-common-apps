import datetime
import logging
import os
import ssl
import string

import pandas
from django.db import models, transaction
from django.conf import settings
from elasticsearch import Elasticsearch, ElasticsearchException
from elasticsearch.connection import create_ssl_context
from elasticsearch_dsl import Search, Q

from poolsched.models import Intention, Job, ArchivedIntention
from cauldron_apps.cauldron.models import Project
from cauldron_apps.poolsched_export.utils import get_jwt_key

ELASTIC_URL = 'https://{}:{}'.format(settings.ES_IN_HOST, settings.ES_IN_PORT)

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()


class ReportsCommitsByMonth(models.Model):
    """Represents a compressed CSV file for all the commits of each project of a user"""
    created = models.DateTimeField()
    location = models.CharField(max_length=150)
    size = models.IntegerField()


class ICommitsByMonthManager(models.Manager):
    """Model manager for instances of ICommitsByMonth"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable ICommitsByMonth intentions for a user

        A intention is selectable if:
        * If it's time for the intention
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of ICommitsByMonth intentions
        """
        intentions = self.filter(user=user,
                                 job=None,
                                 previous=None)
        return intentions.all()[:max]


class ICommitsByMonth(Intention):
    """Intention to export data from a every project as CSV"""
    objects = ICommitsByMonthManager()
    progress = models.CharField(max_length=100, default='pending')

    class Meta:
        db_table = 'poolsched_export_commits'
        verbose_name_plural = "Export Commits Intentions"

    @property
    def process_name(self):
        return 'Export Commits by month'

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """
        # intentions with job and no worker.
        intention = cls.objects \
            .select_related('job') \
            .exclude(job=None).filter(job__worker=None) \
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
        # Any intention is valid as this obtain all the reports from the instance.
        candidates = ICommitsByMonth.objects.all()
        try:
            self.job = candidates[0].job
            self.save()
        except IndexError:
            return None
        return self.job

    def report_commits_by_month(self, report):
        logger.info(f"Get number of commits for {report.id} grouped by month")
        jwt_key = get_jwt_key(f"Project CSV", report.projectrole.backend_role)
        context = create_ssl_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        elastic = Elasticsearch(hosts=[settings.ES_IN_HOST], scheme='https', port=9200,
                                headers={"Authorization": f"Bearer {jwt_key}"},
                                ssl_context=context, timeout=5)

        s = Search(using=elastic, index='git') \
            .filter(~Q('match', files=0)) \
            .extra(size=0)
        s.aggs.bucket('commits_date', 'date_histogram', field='grimoire_creation_date', calendar_interval='month')

        try:
            response = s.execute()
        except ElasticsearchException as e:
            logger.warning(e)
            response = None

        if response is not None and response.success():
            o = response.aggregations.commits_date.to_dict()['buckets']
            # Create a one row DataFrame with one column per date
            c, v = [], []
            for item in o:
                c.append(item['key_as_string'].split('T')[0])
                v.append(item['doc_count'])

            df = pandas.DataFrame(data=[v], columns=c)
        else:
            df = pandas.DataFrame()
        df['report_id'] = report.id
        ch_include = set(string.ascii_letters + string.digits + string.whitespace)
        df['report_name'] = ''.join(ch for ch in report.name if ch in ch_include)
        return df

    def run(self, job):
        """Run the code to fulfill this intention

        :param job: job to be run
        """

        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            logger.info(f"Start exporting commits data")
            created = datetime.datetime.utcnow()

            filename = f"csv/commits-by-month-" \
                       f"{created.strftime('%Y%m%dT%H%M%S')}.csv.gz"

            file_path = os.path.join(settings.STATIC_FILES_DIR, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            df = pandas.DataFrame()
            total = Project.objects.count()
            finished = 0
            for project in Project.objects.all():
                new_df = self.report_commits_by_month(project)
                df = pandas.concat([df, new_df], sort=True, ignore_index=True)
                finished += 1
                self.progress = f'{finished}/{total}'
                self.save()
            df.insert(0, 'report_name', df.pop('report_name'))
            df.insert(0, 'report_id', df.pop('report_id'))

            df.to_csv(file_path, header=True, index=False, compression='gzip')
            size = os.path.getsize(file_path)

            try:
                obj = ReportsCommitsByMonth.objects.get()
                try:
                    os.remove(os.path.join(settings.STATIC_FILES_DIR, obj.location))
                except OSError:
                    pass
                else:
                    logger.info(f"{obj.location} removed")
                ReportsCommitsByMonth.objects.update(size=size,
                                                     location=filename,
                                                     created=created)
            except ReportsCommitsByMonth.DoesNotExist:
                ReportsCommitsByMonth.objects.create(size=size,
                                                     location=filename,
                                                     created=created)
            return True
        except Exception as e:
            logger.exception('Got exception exporting data')
            raise Job.StopException
        finally:
            global_logger.removeHandler(handler)

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        ICommitsByMonthArchived.objects.create(user=self.user,
                                               created=self.created,
                                               status=status,
                                               arch_job=arch_job)
        self.delete()


class ICommitsByMonthArchived(ArchivedIntention):
    @property
    def process_name(self):
        return 'Commits by month archived'

    class Meta:
        db_table = 'poolsched_export_commits_archived'
        verbose_name_plural = "Export Commits Intentions Archived"
