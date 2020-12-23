import logging

from django.db import models, transaction
from django.utils.timezone import now

from cauldron_apps.cauldron.models import Project, GitRepository, GitLabRepository
from cauldron_apps.poolsched_git.api import analyze_git_repo_obj
from cauldron_apps.poolsched_gitlab.api import analyze_gl_repo_obj
from cauldron_apps.poolsched_gitlab.models.base import GLToken, GLInstance
from poolsched.models import Intention, Job, ArchivedIntention

try:
    import gitlab
except ImportError:
    # GitLab only used when running the intention
    pass

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()


class AddGLOwnerManager(models.Manager):
    """Model manager for instances of IAddGLOwner"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IAddGLOwner intentions for a user

        A intention is selectable if:
        * no job is still associated with it
        It's not important if there is other job for the same owner,
        that will be checked later.

        :param user: user requesting the intention
        :param max:  maximum number of intentions to return
        :returns:    list of IAddGLOwner intentions
        """
        token_available = user.gltokens\
            .filter(reset__lt=now())\
            .exists()
        if not token_available:
            logger.debug('No selectable intentions for this user (no token available)')
            return []

        intentions = self.filter(user=user,
                                 previous=None,
                                 job=None)
        return intentions.all()[:max]


class IAddGLOwner(Intention):
    """Intention to get the list of repositories for an owner"""
    objects = AddGLOwnerManager()

    # GitLab owner to get the repositories
    owner = models.CharField(max_length=128)
    # GitLab instance
    instance = models.ForeignKey(GLInstance, on_delete=models.CASCADE, to_field='name', default='GitLab')
    # Project in which this owner should be added
    project = models.ForeignKey(to=Project, on_delete=models.CASCADE)
    # Collect git repositories
    commits = models.BooleanField(default=True)
    # Collect GitLab repositories
    issues = models.BooleanField(default=True)
    # Collect forks:
    forks = models.BooleanField(default=False)
    # Start analysis after retrieving the list
    analyze = models.BooleanField(default=True)

    @property
    def process_name(self):
        return "GL Owner Repositories"

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting

        :return:           selected job (None if none is ready)
        """

        intention = cls.objects\
            .select_related('job')\
            .exclude(job=None).filter(job__worker=None).filter(job__gltoken__reset__lt=now())\
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
        candidates = IAddGLOwner.objects.filter(owner=self.owner,
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
        tokens = GLToken.objects.filter(user=self.user)
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
        tokens = self.user.gltokens.filter(instance=self.instance).all()  # We ignore the limit for owner request
        # Only create the job if there is at least one token
        if tokens:
            job = super().create_job(worker)
            self.refresh_from_db()
            if self.job:
                self.job.gltokens.add(*tokens)
            return job
        return None

    def _get_group_repositories(self, gl, name):
        """Recursive function to get the repositories of a group"""
        logger.info(f"Get repositories from {name}")
        gl_urls, git_urls = [], []
        group = gl.groups.get(name)
        for project in group.projects.list(as_list=False, visibility='public'):
            if hasattr(project, 'forked_from_project') and not self.forks:
                continue
            owner = project.path_with_namespace.split('/')[0]
            repo = '%2F'.join(project.path_with_namespace.split('/')[1:])
            gl_urls.append(f"{owner}/{repo}")
            git_urls.append(project.http_url_to_repo)
        for subgroup in group.subgroups.list(as_list=False, all_available=True):
            if subgroup.visibility != "public":
                continue
            sub_gl_urls, sub_git_urls = self._get_group_repositories(gl, subgroup.full_path)
            gl_urls.extend(sub_gl_urls)
            git_urls.extend(sub_git_urls)
        return gl_urls, git_urls

    def _get_user_repositories(self, gl, name):
        """Get repositories of a user"""
        gl_urls, git_urls = [], []
        users = gl.users.list(username=name)
        user = users[0]
        for project in user.projects.list(as_list=False, visibility='public'):
            if hasattr(project, 'forked_from_project') and not self.forks:
                continue
            owner = project.path_with_namespace.split('/')[0]
            repo = '%2F'.join(project.path_with_namespace.split('/')[1:])
            gl_urls.append(f"{owner}/{repo}")
            git_urls.append(project.http_url_to_repo)
        return gl_urls, git_urls

    def _guess_owner_type(self, gl):
        """Guess if it a Gitlab owner or a user"""
        if gl.users.list(username=self.owner):
            logger.info(f"{self.owner} is a user")
            return 'user'
        try:
            gl.groups.get(self.owner)
            logger.info(f"{self.owner} is a group")
            return 'group'
        except gitlab.exceptions.GitlabGetError:
            pass
        return None

    def _run_owner(self, token):
        gl = gitlab.Gitlab(url=self.instance.endpoint, oauth_token=token)
        owner_type = self._guess_owner_type(gl)
        if owner_type == 'group':
            gl_urls, git_urls = self._get_group_repositories(gl, self.owner)
        elif owner_type == 'user':
            gl_urls, git_urls = self._get_user_repositories(gl, self.owner)
        else:
            raise Job.StopException

        if self.issues:
            for url in gl_urls:
                owner, name = url.split('/')
                logger.info(f"Adding GitLab {owner}/{name} to project {self.project.id}")
                repo, created = GitLabRepository.objects.get_or_create(owner=owner, repo=name, instance=self.instance)
                if not repo.repo_sched:
                    repo.link_sched_repo()
                repo.projects.add(self.project)
                if self.analyze:
                    logger.info(f"Create intention for {repo}")
                    analyze_gl_repo_obj(self.project.creator, repo.repo_sched)
        if self.commits:
            for url in git_urls:
                logger.info(f"Adding Git {url} to project {self.project.id}")
                repo, created = GitRepository.objects.get_or_create(url=url)
                if not repo.repo_sched:
                    repo.link_sched_repo()
                repo.projects.add(self.project)
                if self.analyze:
                    logger.info(f"Create intention for {repo}")
                    analyze_git_repo_obj(self.project.creator, repo.repo_sched)

    def run(self, job):
        """Run the code to fulfill this intention

        :param job: job to be run
        """
        tokens = job.gltokens
        if not tokens:
            logger.error(f'Token not found for intention {self}')
            raise Job.StopException
        token = tokens.filter(reset__lt=now()).first()
        if not token:
            logger.error(f'Token RateLimit before start')
            return False
        logger.info(f"Running IAddGLOwner intention: {self.owner}, token: {token}")

        handler = self._create_log_handler(job)
        try:
            global_logger.addHandler(handler)
            self._run_owner(token.token)
            self.project.update_elastic_role()
            return True
        except Exception as e:
            logger.error(f"Error running IAddGLOwner intention {str(e)}")
            raise Job.StopException
        finally:
            global_logger.removeHandler(handler)

    def archive(self, status=ArchivedIntention.OK, arch_job=None):
        """Archive and remove the current intention"""
        IAddGLOwnerArchived.objects.create(intention_id=self.id,
                                           user=self.user,
                                           created=self.created,
                                           status=status,
                                           arch_job=arch_job,
                                           owner=self.owner,
                                           forks=self.forks,
                                           instance=self.instance,
                                           project=self.project,
                                           commits=self.commits,
                                           issues=self.issues,
                                           analyze=self.analyze)
        self.delete()


class IAddGLOwnerArchived(ArchivedIntention):
    intention_id = models.IntegerField()
    owner = models.CharField(max_length=128)
    instance = models.ForeignKey(GLInstance, on_delete=models.CASCADE, to_field='name', default='GitLab')
    project = models.ForeignKey(to=Project, on_delete=models.SET_NULL, null=True)
    commits = models.BooleanField(default=True)
    forks = models.BooleanField(default=True)
    issues = models.BooleanField(default=True)
    analyze = models.BooleanField(default=True)

    @property
    def process_name(self):
        return "Archived GL Owner Repositories"
