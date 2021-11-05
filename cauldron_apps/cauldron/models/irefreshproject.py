import logging

from django.db import models, transaction

from poolsched.models import Intention, Job, ArchivedIntention
from cauldron_apps.cauldron.models import Project


logger = logging.getLogger(__name__)
global_logger = logging.getLogger()


class RefreshProjectManager(models.Manager):
    """Model manager for instances of IRefreshProject"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IRefreshProject intentions for a user

        A intention is selectable if:
        * no job is still associated with it
        It's not important if there is other job for the same owner,
        that will be checked later.

        :param user: user requesting the intention
        :param max:  maximum number of intentions to return
        :returns:    list of IRefreshProject intentions
        """
        intentions = self.filter(user=user,
                                 previous=None,
                                 job=None)
        return intentions.all()[:max]


class IRefreshProject(Intention):
    """Intention to refresh a project"""
    objects = RefreshProjectManager()

    # Project to refresh
    project = models.ForeignKey(to=Project, on_delete=models.CASCADE)

    @property
    def process_name(self):
        return "Refresh project"

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting

        :return:           selected job (None if none is ready)
        """

        intention = cls.objects\
            .select_related('job')\
            .exclude(job=None).filter(job__worker=None).first()
        if intention:
            return intention.update_job_worker(worker)
        return None

    def running_job(self):
        """Find a Job that satisfies this intention

        If a not done job is found, the intention is assigned
        and the job is returned.

        :return: Job object, if it was found, or None, if not
        """
        candidates = IRefreshProject.objects.filter(project=self.project)
        try:
            # Find intention with job for the same attributes, assign job to self
            self.job = candidates[0].job
            self.save()
        except IndexError:
            # No intention with a job for the same repo found
            return None
        return self.job

    def create_job(self, worker):
        """Create a new job for this intention
        Adds the job to the intention, too.

        If the worker didn't create the job, return None

        A IRaW intention cannot run if there are too many jobs
        using available tokens.

        :param worker: Worker willing to create the job.
        :returns:      Job created by the worker, or None
        """
        tokens = self.user.ghtokens.all()  # We ignore the limit for owner request
        # Only create the job if there is at least one token
        if tokens:
            job = super().create_job(worker)
            self.refresh_from_db()
            if self.job:
                self.job.ghtokens.add(*tokens)
            return job
        return None

    def create_intentions(self):
        """Create intentions for the current project for the analysis"""
        for repo in self.project.repository_set.select_subclasses():
            repo.refresh(self.user)

    def run(self, job):
        """Run the code to fulfill this intention

        :param job: job to be run
        """
        logger.info(f"Running IRefreshProject intention: {self.project.id}")

        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            self.create_intentions()
            return True
        except Exception as e:
            logger.error(f"Error running IRefreshProject intention {str(e)}")
            raise Job.StopException
        finally:
            global_logger.removeHandler(handler)

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        IRefreshProjectArchived.objects.create(intention_id=self.id,
                                               user=self.user,
                                               created=self.created,
                                               status=status,
                                               arch_job=arch_job,
                                               project=self.project)
        self.delete()


class IRefreshProjectArchived(ArchivedIntention):
    intention_id = models.IntegerField()
    project = models.ForeignKey(to=Project, on_delete=models.SET_NULL, null=True)

    @property
    def process_name(self):
        return "Archived refresh project"
