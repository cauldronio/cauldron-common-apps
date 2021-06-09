import datetime
import logging

from django.db import models, transaction
from django.utils.timezone import now

from poolsched.models import Intention, Job, ArchivedIntention
from cauldron_apps.cauldron.models import Project, GitHubRepository, GitRepository, RepositoryMetrics
from cauldron_apps.poolsched_github.models import GHToken, GHInstance
from cauldron_apps.poolsched_git.api import analyze_git_repo_obj
from cauldron_apps.poolsched_github.api import analyze_gh_repo_obj

try:
    from github import Github, RateLimitExceededException
except ImportError:
    # Github only used when running the intention
    pass

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()


class AddGHOwnerManager(models.Manager):
    """Model manager for instances of IAddGHOwner"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IAddGHOwner intentions for a user

        A intention is selectable if:
        * no job is still associated with it
        It's not important if there is other job for the same owner,
        that will be checked later.

        :param user: user requesting the intention
        :param max:  maximum number of intentions to return
        :returns:    list of IAddGHOwner intentions
        """
        token_available = user.ghtokens\
            .filter(reset__lt=now())\
            .exists()
        if not token_available:
            logger.debug('No selectable intentions for this user (no token available)')
            return []

        intentions = self.filter(user=user,
                                 previous=None,
                                 job=None)
        return intentions.all()[:max]


class IAddGHOwner(Intention):
    """Intention to get the list of repositories for an owner"""
    objects = AddGHOwnerManager()

    # GitHub owner to get the repositories
    owner = models.CharField(max_length=128)
    # GitHub instance for the owner
    instance = models.ForeignKey(GHInstance, to_field='name', default='GitHub', on_delete=models.CASCADE)
    # Project in which this owner should be added
    project = models.ForeignKey(to=Project, on_delete=models.CASCADE)
    # Collect git repositories
    commits = models.BooleanField(default=True)
    # Collect github repositories
    issues = models.BooleanField(default=True)
    # Collect forks:
    forks = models.BooleanField(default=False)
    # Start analysis after retrieving the list
    analyze = models.BooleanField(default=True)

    @property
    def process_name(self):
        return "GH Owner Repositories"

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting

        :return:           selected job (None if none is ready)
        """

        intention = cls.objects\
            .select_related('job')\
            .exclude(job=None).filter(job__worker=None).filter(job__ghtoken__reset__lt=now())\
            .first()
        if intention:
            return intention.update_job_worker(worker)
        return None

    def running_job(self):
        """Find a Job that satisfies this intention

        If a not done job is found, the intention is assigned
        and the job is returned.

        :return: Job object, if it was found, or None, if not
        """
        candidates = IAddGHOwner.objects.filter(owner=self.owner,
                                                commits=self.commits,
                                                issues=self.issues,
                                                forks=self.forks,
                                                analyze=self.analyze,
                                                instance=self.instance,
                                                project=self.project,
                                                job__isnull=False)
        try:
            # Find intention with job for the same attributes, assign job to self
            self.job = candidates[0].job
            self.save()
        except IndexError:
            # No intention with a job for the same repo found
            return None

        # Get tokens for the user, and assign them to job
        tokens = GHToken.objects.filter(user=self.user)
        token_included = False
        for token in tokens:
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
        tokens = self.user.ghtokens.all()  # We ignore the limit for owner request
        # Only create the job if there is at least one token
        if tokens:
            job = super().create_job(worker)
            self.refresh_from_db()
            if self.job:
                self.job.ghtokens.add(*tokens)
            return job
        return None

    def _run_owner(self, token):
        github = Github(token)
        try:
            repositories = github.get_user(self.owner).get_repos()
            for repo_gh in repositories:
                name = f'GitHub {self.owner}/{repo_gh.name}'
                result, _ = RepositoryMetrics.objects.get_or_create(name=name)
                if repo_gh.fork and not self.forks:
                    continue
                if self.issues:
                    logger.info(f"Adding GitHub {self.owner}/{repo_gh.name} to project {self.project.id}")
                    repo, created = GitHubRepository.objects.get_or_create(owner=self.owner,
                                                                           repo=repo_gh.name,
                                                                           defaults={'metrics': result})
                    if not repo.repo_sched:
                        repo.link_sched_repo()
                    repo.projects.add(self.project)
                    if self.analyze:
                        logger.info(f"Create intention for {repo}")
                        analyze_gh_repo_obj(self.project.creator, repo.repo_sched)
                if self.commits:
                    logger.info(f"Adding Git {repo_gh.clone_url} to project {self.project.id}")
                    repo, created = GitRepository.objects.get_or_create(url=repo_gh.clone_url,
                                                                        defaults={'metrics': result})
                    if not repo.repo_sched:
                        repo.link_sched_repo()
                    repo.projects.add(self.project)
                    if self.analyze:
                        logger.info(f"Create intention for {repo}")
                        analyze_git_repo_obj(self.project.creator, repo.repo_sched)
        except RateLimitExceededException:
            utcnow = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).timestamp()
            time_to_reset = github.rate_limiting_resettime - (utcnow + 1)
            time_to_reset = 0 if time_to_reset < 0 else time_to_reset
            return time_to_reset

    def run(self, job):
        """Run the code to fulfill this intention

        :param job: job to be run
        """
        tokens = job.ghtokens
        if not tokens:
            logger.error(f'Token not found for intention {self}')
            raise Job.StopException
        token = tokens.filter(reset__lt=now()).first()
        if not token:
            logger.error(f'Token RateLimit before start')
            return False
        logger.info(f"Running IAddGHOwner intention: {self.owner}, token: {token}")

        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            time_to_reset = self._run_owner(token.token)
            self.project.update_elastic_role()
            if time_to_reset:
                token.reset = now() + datetime.timedelta(minutes=time_to_reset)
                token.save()
                logger.error(f"Rate Limit reached. Retry at {token.reset}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error running IAddGHOwner intention {str(e)}")
            raise Job.StopException
        finally:
            global_logger.removeHandler(handler)

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        IAddGHOwnerArchived.objects.create(intention_id=self.id,
                                           user=self.user,
                                           created=self.created,
                                           status=status,
                                           arch_job=arch_job,
                                           forks=self.forks,
                                           owner=self.owner,
                                           instance=self.instance,
                                           project=self.project,
                                           commits=self.commits,
                                           issues=self.issues,
                                           analyze=self.analyze)
        self.delete()


class IAddGHOwnerArchived(ArchivedIntention):
    intention_id = models.IntegerField()
    owner = models.CharField(max_length=128)
    instance = models.ForeignKey(GHInstance, on_delete=models.CASCADE, to_field='name', default='GitHub')
    project = models.ForeignKey(to=Project, on_delete=models.SET_NULL, null=True)
    commits = models.BooleanField(default=True)
    forks = models.BooleanField(default=True)
    issues = models.BooleanField(default=True)
    analyze = models.BooleanField(default=True)

    @property
    def process_name(self):
        return "Archived GH Owner Repositories"
