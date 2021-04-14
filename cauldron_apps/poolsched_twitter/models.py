import logging

from django.db import models, transaction
from django.conf import settings
from django.urls import reverse

from poolsched.models import Intention, Job, ArchivedIntention
from ..cauldron.models import OauthUser

from datetime import datetime, timedelta
import pytz
import tweepy

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = "poolsched_twitter"


class ITwitterNotifyManager(models.Manager):
    """Model manager for instances of ITwitterNotify"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable ITwitterNotify intentions for a user

        A intention is selectable for a user if:
        * No job is assigned
        * Doesn't depend on previous intentions
        * Related project has no dependent intentions
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of ITwitterNotify intentions
        """
        ready_intentions = []
        intentions = self.filter(user=user,
                                 job=None,
                                 previous=None)

        for intention in intentions:
            dependent_intentions = intention.project.repos_running() + \
                                   intention.project.iaddghowner_set.count() + \
                                   intention.project.iaddglowner_set.count()

            if dependent_intentions == 0:
                ready_intentions.append(intention)

        return ready_intentions[:max]


class ITwitterNotify(Intention):
    """Intention to notify a user with Twitter when a project is completely
       analyzed and has no pending intentions"""
    objects = ITwitterNotifyManager()

    project = models.ForeignKey('cauldron.project', on_delete=models.CASCADE)

    report_url = models.URLField()

    class Meta:
        db_table = TABLE_PREFIX + '_intention'
        verbose_name_plural = 'Twitter Notify Intentions'

    @property
    def process_name(self):
        return 'Twitter Notification'

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting

        :return:           selected job (None if none is ready)
        """

        # This method should never run because this kind of intentions
        # are never rescheduled but we provide the same implementation
        # as selectable_intentions

        intentions = cls.objects \
            .select_related('job') \
            .exclude(job=None).filter(job__worker=None)

        intention = None
        for intention in intentions:
            dependent_intentions = intention.project.repos_running() + \
                                   intention.project.iaddghowner_set.count() + \
                                   intention.project.iaddglowner_set.count()

            if dependent_intentions == 0:
                break

        if intention:
            return intention.update_job_worker(worker)

        return None

    def running_job(self):
        """Find a job that would satisfy this intention
        In this case there shouldn't be any other intention
        """
        return None

    def run(self, job):
        """Run the code to fulfill this intention

        :param job: job to be run
        """

        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            logger.info('Create a tweet')

            try:
                user = self.project.creator
                twitter_user = OauthUser.objects.get(backend='twitter', user=user)
                twitter_username = twitter_user.username
            except OauthUser.DoesNotExist as e:
                logger.error(f'User {user.first_name} has not a Twitter linked account: {str(e)}')

            # Authenticate to Twitter
            auth = tweepy.OAuthHandler(settings.TWITTER_CLIENT_ID, settings.TWITTER_CLIENT_SECRET)
            auth.set_access_token(settings.TWITTER_ACCESS_TOKEN, settings.TWITTER_ACCESS_TOKEN_SECRET)

            # Create API object
            api = tweepy.API(auth)

            # Construct the message
            message = f'Hey @{twitter_username}! The report you requested '
            difference = datetime.utcnow().replace(tzinfo=pytz.utc) - self.created
            if difference.days > 0:
                message += f'{difference.days} days, '
            hours, remainder = divmod(difference.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                message += f'{hours} hours, '

            message += f'{minutes} minutes ago is ready! {self.report_url}'
            # Create a tweet
            api.update_status(message)

            return True
        except Exception as e:
            logger.error(f"Error running ITwitterNotify: {str(e)}")
            raise Job.StopException
        finally:
            global_logger.removeHandler(handler)

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        ITwitterNotifyArchived.objects.create(user=self.user,
                                              created=self.created,
                                              status=status,
                                              arch_job=arch_job,
                                              project=self.project)
        self.delete()


class ITwitterNotifyArchived(ArchivedIntention):
    project = models.ForeignKey('cauldron.project', on_delete=models.CASCADE)

    @property
    def process_name(self):
        return 'Twitter Notify Archived'

    class Meta:
        db_table = TABLE_PREFIX + '_archived'
        verbose_name_plural = 'Twitter Notify Archived'
