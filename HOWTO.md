- Create your environment for the repository and activate it (virtualenv)

- In `requirements.txt` change (you can omit this step, but in the future you may need to install the package again):
    ```
    - git+https://gitlab.com/cauldronio/cauldron-pool-scheduler.git
    + -e /location/of/cauldron-pool-scheduler
    ```
  This will install the poolsched package and any changed to poolsched will be shown in this environment.

- Install the packages:

    `pip install -r requirements.txt`

- Create an app:

    `python manage.py startapp app_name`

- Move the app inside cauldron_common_apps

    `mv app_name cauldron_common_apps/`

- Install the app in all the projects used (like `cauldron-web` and `cauldron-poolsched-worker`)

- Take the following template for the intention you want to create. Change INTENTION_NAME with the name of the model for the intention and complete the TODO elements and change the functions to fulfill the intention.

```python
import logging

from django.db import models, transaction

from poolsched.models import Intention, Job, ArchivedIntention

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()


class INTENTION_NAMEManager(models.Manager):
    """Model manager for instances of INTENTION_NAME"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable INTENTION_NAME intentions for a user

        A intention is selectable if:
        * If it's time for the intention
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of INTENTION_NAME intentions
        """
        # TODO: Include more filters depending on your intention
        intentions = self.filter(user=user,
                                 job=None,
                                 previous=None)
        return intentions.all()[:max]


class INTENTION_NAME(Intention):
    """Intention to INTENTION_DESCRIPTION"""
    objects = INTENTION_NAMEManager()

    # TODO: Add attributes

    class Meta:
        db_table = 'poolsched_INTENTION_NAME'  # TODO: CHANGE
        verbose_name_plural = "INTENTION_NAME"  # TODO: CHANGE

    @property
    def process_name(self):
        return 'INTENTION_NAME'  # TODO: CHANGE

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """
        # TODO: CHANGE
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
        # TODO: CHANGE
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

        :param job: job to be run
        """

        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            logger.info(f"Running INTENTION_NAME")
            runner = 0
            runner.run()
            logger.info(f"Finished without errors")
            return True
        except Exception as e:
            logger.error(f"Error running INTENTION_NAME: {str(e)}")
            raise Job.StopException
        finally:
            global_logger.removeHandler(handler)

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        INTENTION_NAMEArchived.objects.create(user=self.user,
                                              created=self.created,
                                              status=status,
                                              arch_job=arch_job,
                                              )  # TODO: Add parameters
        self.delete()


class INTENTION_NAMEArchived(ArchivedIntention):
    # TODO: Add attributes

    @property
    def process_name(self):
        return 'INTENTION_NAME'  # TODO: CHANGE

    class Meta:
        db_table = 'poolsched_INTENTION_NAME_archived'  # TODO: CHANGE
        verbose_name_plural = "MINTENTION_NAME Archived"  # TODO:CHANGE


```
