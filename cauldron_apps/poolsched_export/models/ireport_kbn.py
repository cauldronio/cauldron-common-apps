import base64
import datetime
import logging
import os
from zipfile import ZipFile

import requests
from django.conf import settings
from django.db import models, transaction
from django.utils.timezone import now

from .. import utils

from poolsched.models import Intention, Job, ArchivedIntention

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

KIB_IN_URL = "http://{}:{}{}".format(settings.KIB_IN_HOST, settings.KIB_IN_PORT, settings.KIB_PATH)


def one_year_before():
    return now() - datetime.timedelta(days=365)


class ProjectKibanaReport(models.Model):
    """Represents a Kibana report file for a project"""
    project = models.ForeignKey('cauldron.Project', on_delete=models.CASCADE, related_name='kbn_report')
    dashboard = models.CharField(max_length=200, default='all')
    dashboard_name = models.CharField(max_length=200, default='All dashboards')
    format = models.CharField(max_length=20, default='pdf')
    created = models.DateTimeField(auto_now_add=True)
    from_date = models.DateTimeField(default=one_year_before)
    to_date = models.DateTimeField(default=now)
    location = models.CharField(max_length=150, null=True, default=None)
    progress = models.CharField(max_length=100, default='pending')


class IReportKbnManager(models.Manager):
    """Model manager for instances of IReportKbn"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IReportKbn intentions for a user

        A intention is selectable if:
        * If it's time for the intention
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IReportKbn intentions
        """
        intentions = self.filter(user=user,
                                 job=None,
                                 previous=None)
        return intentions.all()[:max]


class IReportKbn(Intention):
    """Intention to create Kibana reports from a project"""
    objects = IReportKbnManager()

    kbn_report = models.ForeignKey(ProjectKibanaReport, on_delete=models.CASCADE, related_name='ikbn_report')

    class Meta:
        db_table = 'poolsched_kbn_report'
        verbose_name_plural = "Kibana report intention"

    @property
    def process_name(self):
        return 'Kibana Report'

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

    def running_job(self):
        """Find a job that would satisfy this intention

        If a not done job is found, which would satisfy intention,
        the intention is assigned to that job, which is returned.
        The user token is assigned to it, too.

        :return:          Job object, if it was found, or None, if not
        """
        candidates = self.__class__.objects.filter(kbn_report=self.kbn_report,
                                                   job__isnull=False)
        try:
            # Find intention with job for the same repo, assign job to self
            self.job = candidates[0].job
            self.save()
        except IndexError:
            # No intention with a job for the same repo found
            return None
        return self.job

    def _export_kibana_report(self, client, dashboard, name):
        """
        Export a Kibana report given the dashboard id and a requests authenticated session
        :return: location of the file
        """
        from_date_str = self.kbn_report.from_date.strftime('%Y-%m-%dT%H:%M:%S')
        to_date_str = self.kbn_report.to_date.strftime('%Y-%m-%dT%H:%M:%S')
        hours = int((self.kbn_report.from_date - self.kbn_report.to_date).seconds / 3600)
        url = f'{KIB_IN_URL}/api/reporting/generateReport?timezone=Europe/Madrid'
        headers = {
            "kbn-version": "7.10.2",
            "origin": "https://cauldron.io"
        }
        data = {
            'query_url': f"/kibana/app/dashboards?security_tenant=global#/view/{dashboard}"
                         f"?_g=(time:(from:'{from_date_str}',to:'{to_date_str}'))",
            'time_from': int(self.kbn_report.from_date.timestamp() * 1000),
            'time_to': int(self.kbn_report.to_date.timestamp() * 1000),
            'report_definition': {
                'report_params': {
                    'report_name': 'On_demand_report',
                    'report_source': 'Dashboard',
                    'description': 'In-context report download',
                    'core_params': {
                        'base_url': f'/kibana/app/dashboards#/view/{dashboard}',
                        'report_format': self.kbn_report.format,
                        'time_duration': f'PT{hours}H'
                    }
                },
                'delivery': {
                    'delivery_type': 'Kibana user',
                    'delivery_params': {
                        'kibana_recipients': []
                    }
                },
                'trigger': {
                    'trigger_type': 'On demand'
                }
            }
        }
        r = client.post(url=url, json=data, headers=headers, timeout=None)

        if r.ok:
            response_data = r.json()
            filename = f"report/{name.replace(' ', '_')}.{self.kbn_report.format}"
            file_path = os.path.join(settings.STATIC_FILES_DIR, filename)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as f:
                f.write(base64.b64decode(response_data['data']))
            return filename
        logger.error(r.text)
        return None

    def export_kibana_report(self):
        self.kbn_report.progress = '0/1'
        self.kbn_report.save()
        jwt_key = utils.get_jwt_key(f"Public {self.kbn_report.project.id}",
                                    [self.kbn_report.project.projectrole.backend_role, 'br_download_reports'])
        with requests.Session() as client:
            client.get(url=f"{KIB_IN_URL}/", params={'jwtToken': jwt_key})
            filename = self._export_kibana_report(client, self.kbn_report.dashboard, self.kbn_report.dashboard_name)
            if filename:
                self.kbn_report.location = filename
                self.kbn_report.progress = '1/1'
                self.kbn_report.save()
            else:
                self.kbn_report.progress = ''
                self.kbn_report.save()
                raise Exception('Could not export that dashboard')

    def export_all_kibana_reports(self):
        exported_files = []
        dashboards = utils.get_available_dashboards(self.kbn_report.project, KIB_IN_URL)
        total = len(dashboards)
        self.kbn_report.progress = f'0/{total}'
        self.kbn_report.save()
        jwt_key = utils.get_jwt_key(f"Public {self.kbn_report.project.id}",
                                    [self.kbn_report.project.projectrole.backend_role, 'br_download_reports'])
        with requests.Session() as client:
            client.get(url=f"{KIB_IN_URL}/", params={'jwtToken': jwt_key})
            for dashboard in dashboards:
                logger.info(f'Generating dashboard {dashboard["name"]}')
                dash_id = dashboard['id']
                filename = self._export_kibana_report(client, dash_id, dashboard["name"])
                if filename:
                    file_path = os.path.join(settings.STATIC_FILES_DIR, filename)
                    exported_files.append(file_path)
                self.kbn_report.progress = f'{len(exported_files)}/{total}'
                self.kbn_report.save()

        zip_name = f"report/report-{self.kbn_report.project.id}-" \
                   f"from{self.kbn_report.from_date.strftime('%Y%m%d')}-" \
                   f"to{self.kbn_report.from_date.strftime('%Y%m%d')}-" \
                   f"created{self.kbn_report.created.strftime('%Y%m%dT%H%M%S')}.zip"
        zip_path = os.path.join(settings.STATIC_FILES_DIR, zip_name)
        with ZipFile(zip_path, 'w') as myzip:
            for f in exported_files:
                myzip.write(f, arcname=os.path.basename(f))
        self.kbn_report.location = zip_name
        self.kbn_report.save()

    def run(self, job):
        """Run the code to fulfill this intention

        :param job: job to be run
        """

        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            logger.info(f"Running IReportKbn")
            if self.kbn_report.dashboard == 'all':
                self.export_all_kibana_reports()
            else:
                self.export_kibana_report()
            logger.info(f"Finished without errors")
            return True
        except Exception as e:
            self.kbn_report.progress = ''
            self.kbn_report.save()
            logger.exception(f"Error running IReportKbn: {str(e)}")
            raise Job.StopException
        finally:
            global_logger.removeHandler(handler)

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        IReportKbnArchived.objects.create(user=self.user,
                                          created=self.created,
                                          status=status,
                                          arch_job=arch_job,
                                          kbn_report=self.kbn_report)
        self.delete()


class IReportKbnArchived(ArchivedIntention):
    kbn_report = models.ForeignKey(ProjectKibanaReport, on_delete=models.CASCADE, related_name='ikbn_report_archived')

    @property
    def process_name(self):
        return 'Kibana Report Archived'

    class Meta:
        db_table = 'poolsched_kbn_report_archived'
        verbose_name_plural = "Kibana Report Archived"


