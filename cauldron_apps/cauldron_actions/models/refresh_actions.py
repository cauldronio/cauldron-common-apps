import logging

from django.db import models, transaction

from poolsched.models import Intention, Job, ArchivedIntention

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()


class IRefreshActionsManager(models.Manager):
    """Model manager for instances of IRefreshActions"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IRefreshActions intentions for a user

        A intention is selectable if:
        * If it's time for the intention
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IRefreshActions intentions
        """
        intentions = self.filter(user=user,
                                 job=None,
                                 previous=None)
        return intentions.all()[:max]


class IRefreshActions(Intention):
    """Intention to INTENTION_DESCRIPTION"""
    objects = IRefreshActionsManager()

    project = models.ForeignKey('cauldron.project', on_delete=models.CASCADE)

    class Meta:
        db_table = 'poolsched_IRefreshActions'
        verbose_name_plural = "Refresh Actions Intentions"

    @property
    def process_name(self):
        return 'Refresh Actions'

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

        candidates = IRefreshActions.objects.filter(job__isnull=False).filter(project=self.project)
        try:
            # Find intention with job for the same repo, assign job to self
            self.job = candidates[0].job
            self.save()
        except IndexError:
            # No intention with a job for the same repo found
            return None
        return self.job

    def _refresh_actions(self):
        any_action = self.project.action_set.count() > 0
        if not any_action:
            logger.info('No actions defined for this project')
            # To avoid removing repositories from projects without actions
            return
        logger.info('Removing all the repositories')
        for repo in self.project.repository_set.select_subclasses():
            repo.remove_intentions(self.user)
        self.project.repository_set.clear()
        self.project.update_elastic_role()

        logger.info('Run every action defined')
        for action in self.project.action_set.order_by('created').select_subclasses():
            logger.info(f'Run {action.name_ui}')
            action.run()
        self.project.update_elastic_role()

        # Refresh data
        logging.info('Refresh repositories')
        for repo in self.project.repository_set.select_subclasses():
            repo.refresh(self.project.creator)

    def run(self, job):
        """Run the code to fulfill this intention

        :param job: job to be run
        """

        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            logger.info(f"Running IRefreshActions")
            self._refresh_actions()
            logger.info(f"Finished without errors")
            return True
        except Exception as e:
            logger.error(f"Error running IRefreshActions: {str(e)}")
            raise Job.StopException
        finally:
            global_logger.removeHandler(handler)

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        IRefreshActionsArchived.objects.create(user=self.user,
                                               created=self.created,
                                               status=status,
                                               arch_job=arch_job,
                                               project=self.project)
        self.delete()


class IRefreshActionsArchived(ArchivedIntention):

    project = models.ForeignKey('cauldron.project', null=True, on_delete=models.SET_NULL)

    @property
    def process_name(self):
        return 'IRefreshActions Archived'

    class Meta:
        db_table = 'poolsched_IRefreshActions_archived'
        verbose_name_plural = "RefreshActions Intentions Archived"
