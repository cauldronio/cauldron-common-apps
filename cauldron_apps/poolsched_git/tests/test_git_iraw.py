import logging

from django.test import TestCase
from django.contrib.auth import get_user_model

from poolsched.models import Job, Worker
from ..models import GitRepo, IGitRaw

User = get_user_model()

logger = logging.getLogger(__name__)


class TestBasic(TestCase):

    def test_create(self):
        """Insert a single IGitRaw into the database"""
        repo = GitRepo.objects.create(
            url='https://github.com/my-org/project')
        iraw = IGitRaw.objects.create(repo=repo)
        found = IGitRaw.objects.get(repo=repo)
        self.assertEqual(iraw, found)

    def test_create_2(self):
        """Insert two IGitRaw into the database"""
        repo1 = GitRepo.objects.create(
            url='https://github.com/my-org/project-1')
        repo2 = GitRepo.objects.create(
            url='https://github.com/my-org/project-2')

        iraw1 = IGitRaw.objects.create(repo=repo1)
        iraw2 = IGitRaw.objects.create(repo=repo2)

        iraws = IGitRaw.objects.all()
        self.assertEqual(len(iraws), 2)
        self.assertIn(iraw1, iraws)
        self.assertIn(iraw2, iraws)


class TestMethods(TestCase):

    def setUp(self):
        self.repo1 = GitRepo.objects.create(
            url='https://github.com/my-org/project-1')
        self.user1 = User.objects.create(username='A')
        self.user2 = User.objects.create(username='B')
        self.iraw1 = IGitRaw.objects.create(repo=self.repo1, user=self.user1)
        self.iraw2 = IGitRaw.objects.create(repo=self.repo1, user=self.user2)
        self.worker1 = Worker.objects.create()
        self.worker2 = Worker.objects.create()

    def test_create_previous(self):
        """Test create previous method"""
        prev = self.iraw1.create_previous()
        self.assertEqual(prev, [])

    def test_create_job(self):
        """Test create IGitRaw job"""
        job = self.iraw1.create_job(self.worker1)
        self.assertEqual(job.worker, self.worker1)
        self.assertEqual(self.iraw1.job, job)

    def test_create_job2(self):
        """Test create IGitRaw job with existing job"""
        job1 = self.iraw1.create_job(self.worker1)
        job2 = self.iraw1.create_job(self.worker1)
        self.assertEqual(job1.worker, self.worker1)
        self.assertEqual(job2, None)

    def test_running_job(self):
        """Test find a job for iraw1 that doesn't exist"""
        job = self.iraw1.running_job()
        self.assertEqual(job, None)

    def test_running_job2(self):
        """Test find a job for iraw1 that exists"""
        new_job = Job.objects.create()
        self.iraw2.job = new_job
        self.iraw2.save()
        job = self.iraw1.running_job()
        self.assertEqual(job, new_job)


class TestSelectableIntentions(TestCase):

    def setUp(self):
        """
        User 1: 0 intentions
        User 2: 1 intention ready
        User 3: 2 intention ready
        User 5: 1 intention ready, 1 intention with Job
        :return:
        """
        self.repo1 = GitRepo.objects.create(url='https://github.com/my-org/project-1')
        self.repo2 = GitRepo.objects.create(url='https://github.com/my-org/project-2')

        self.user1 = User.objects.create(username='1')

        self.user2 = User.objects.create(username='2')
        self.iraw_U2_1 = IGitRaw.objects.create(repo=self.repo1, user=self.user2)

        self.user3 = User.objects.create(username='3')
        self.iraw_U3_1 = IGitRaw.objects.create(repo=self.repo1, user=self.user3)
        self.iraw_U3_2 = IGitRaw.objects.create(repo=self.repo2, user=self.user3)

        self.user5 = User.objects.create(username='5')
        self.iraw_U5_1 = IGitRaw.objects.create(repo=self.repo1, user=self.user5)
        self.job_U5 = Job.objects.create()
        self.iraw_U5_2 = IGitRaw.objects.create(repo=self.repo2, user=self.user5,
                                                job=self.job_U5)

    def test_user_1(self):
        """Test not available intentions"""
        intentions = IGitRaw.objects.selectable_intentions(user=self.user1)
        self.assertEqual(len(intentions), 0)

    def test_user_2(self):
        """Test one intention ready"""
        intentions = IGitRaw.objects.selectable_intentions(user=self.user2)
        self.assertEqual(len(intentions), 1)
        self.assertEqual(intentions[0], self.iraw_U2_1)

    def test_user_3(self):
        """Test two intentions ready, get 1"""
        intentions = IGitRaw.objects.selectable_intentions(user=self.user3, max=1)
        self.assertEqual(len(intentions), 1)
        self.assertIn(intentions[0], [self.iraw_U3_1, self.iraw_U3_2])

    def test_user_3b(self):
        """Test two intentions ready, get 2"""
        intentions = IGitRaw.objects.selectable_intentions(user=self.user3, max=2)
        self.assertEqual(len(intentions), 2)
        self.assertListEqual(list(intentions), [self.iraw_U3_1, self.iraw_U3_2])

    def test_user_5(self):
        """Test one ready and one ready with job"""
        intentions = IGitRaw.objects.selectable_intentions(user=self.user5, max=2)
        self.assertEqual(len(intentions), 1)
