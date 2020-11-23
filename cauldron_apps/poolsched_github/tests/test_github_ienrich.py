import logging

from django.test import TestCase
from django.contrib.auth import get_user_model

from poolsched.models import Job, Worker
from ..models import GHInstance, GHRepo, IGHEnrich

User = get_user_model()

GITHUB_INSTANCE = GHInstance.objects.get(name='GitHub')

logger = logging.getLogger(__name__)


class TestBasicCreate(TestCase):

    def test_create(self):
        """Insert a single IEnrich into the database"""
        repo = GHRepo.objects.create(owner='owner', repo='repo',
                                     instance=GITHUB_INSTANCE)
        enrich = IGHEnrich.objects.create(repo=repo)
        found = IGHEnrich.objects.get(repo=repo)
        self.assertEqual(enrich, found)

    def test_create_2(self):
        """Insert two IEnrich into the database"""
        repo1 = GHRepo.objects.create(owner='owner1', repo='repo',
                                      instance=GITHUB_INSTANCE)
        repo2 = GHRepo.objects.create(owner='owner2', repo='repo',
                                      instance=GITHUB_INSTANCE)

        enrich1 = IGHEnrich.objects.create(repo=repo1)
        enrich2 = IGHEnrich.objects.create(repo=repo2)

        enrichs = IGHEnrich.objects.all()
        self.assertEqual(len(enrichs), 2)
        self.assertIn(enrich1, enrichs)
        self.assertIn(enrich2, enrichs)


class TestMethods(TestCase):

    def setUp(self):
        self.repo1 = GHRepo.objects.create(owner='owner1', repo='repo',
                                           instance=GITHUB_INSTANCE)
        self.user1 = User.objects.create(username='A')
        self.user2 = User.objects.create(username='B')
        self.enrich1 = IGHEnrich.objects.create(repo=self.repo1, user=self.user1)
        self.enrich2 = IGHEnrich.objects.create(repo=self.repo1, user=self.user2)
        self.worker1 = Worker.objects.create()
        self.worker2 = Worker.objects.create()

    def test_create_previous(self):
        """Test create previous method"""
        prev = self.enrich1.create_previous()
        self.assertEqual(prev[0].repo, self.enrich1.repo)
        self.assertEqual(prev[0].user, self.enrich1.user)

    def test_create_previous_twice(self):
        """Test create previous method two times"""
        prev1 = self.enrich1.create_previous()
        prev2 = self.enrich1.create_previous()
        self.assertEqual(len(prev1), len(prev2))
        self.assertListEqual(prev1, prev2)

    def test_create_job(self):
        """Test create GitHub.IGHEnrich job"""
        job = self.enrich1.create_job(self.worker1)
        self.assertEqual(job.worker, self.worker1)
        self.assertEqual(self.enrich1.job, job)

    def test_create_job2(self):
        """Test create GitHub.IGHEnrich job with existing job"""
        job1 = self.enrich1.create_job(self.worker1)
        job2 = self.enrich1.create_job(self.worker1)
        self.assertEqual(job1.worker, self.worker1)
        self.assertEqual(job2, None)

    def test_running_job(self):
        """Test find a job for enrich1 that doesn't exist"""
        job = self.enrich1.running_job()
        self.assertEqual(job, None)

    def test_running_job2(self):
        """Test find a job for enrich2 that exists"""
        new_job = Job.objects.create()
        self.enrich1.job = new_job
        self.enrich1.save()
        job = self.enrich2.running_job()
        self.assertEqual(job, new_job)


class TestSelectableIntentions(TestCase):
    def setUp(self):
        """Some predefined objects for the tests"""
        self.user = User.objects.create(username='1')
        self.repo1 = GHRepo.objects.create(owner='owner1', repo='repo1',
                                           instance=GITHUB_INSTANCE)
        self.repo2 = GHRepo.objects.create(owner='owner1', repo='repo2',
                                           instance=GITHUB_INSTANCE)

    def test_selectable_1(self):
        """Test not available intentions"""
        intentions = IGHEnrich.objects.selectable_intentions(user=self.user)

        self.assertEqual(len(intentions), 0)

    def test_selectable_2(self):
        """Test one intention ready"""
        ienrich = IGHEnrich.objects.create(repo=self.repo1, user=self.user)
        intentions = IGHEnrich.objects.selectable_intentions(user=self.user)
        self.assertEqual(len(intentions), 1)
        self.assertEqual(intentions[0], ienrich)

    def test_selectable_3(self):
        """Test two intentions ready, get 1"""
        ienrich1 = IGHEnrich.objects.create(repo=self.repo1, user=self.user)
        ienrich2 = IGHEnrich.objects.create(repo=self.repo2, user=self.user)
        intentions = IGHEnrich.objects.selectable_intentions(user=self.user, max=1)
        self.assertEqual(len(intentions), 1)
        self.assertIn(intentions[0], [ienrich1, ienrich2])

    def test_selectable_4(self):
        """Test two intentions ready, get 2"""
        ienrich1 = IGHEnrich.objects.create(repo=self.repo1, user=self.user)
        ienrich2 = IGHEnrich.objects.create(repo=self.repo2, user=self.user)
        intentions = IGHEnrich.objects.selectable_intentions(user=self.user, max=2)
        self.assertEqual(len(intentions), 2)
        self.assertListEqual(list(intentions), [ienrich1, ienrich2])

    def test_selectable_6(self):
        """Test one ready and one ready with job"""
        ienrich = IGHEnrich.objects.create(repo=self.repo1, user=self.user)
        job = Job.objects.create()
        ienrich2 = IGHEnrich.objects.create(repo=self.repo2, user=self.user,
                                            job=job)
        intentions = IGHEnrich.objects.selectable_intentions(user=self.user, max=2)
        self.assertEqual(len(intentions), 1)
        self.assertEqual(intentions[0], ienrich)

    def test_selectable_7(self):
        """Test one ready with previous works pending"""
        job = Job.objects.create()
        ienrich = IGHEnrich.objects.create(repo=self.repo1, user=self.user)
        prev = ienrich.create_previous()
        intentions_enrich = IGHEnrich.objects.selectable_intentions(user=self.user, max=10)
        self.assertEqual(len(intentions_enrich), 0)
        prev_intention = prev[0]
        prev_intention.delete()
        intentions_enrich = IGHEnrich.objects.selectable_intentions(user=self.user, max=10)
        self.assertEqual(len(intentions_enrich), 1)
        self.assertEqual(intentions_enrich[0], ienrich)
