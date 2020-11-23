from django.test import TestCase
from django.db import IntegrityError

from ..models import GitRepo


class TestBasic(TestCase):

    def test_basic(self):
        """Basic tests."""

        repo = GitRepo.objects.create(url='https://github.com/my-org/project')

        found = GitRepo.objects.get(url='https://github.com/my-org/project')
        self.assertEqual(found, repo)

    def test_unique(self):
        """Pair (owner, repo) are unique for the same instance."""

        GitRepo.objects.create(url='https://github.com/my-org/project')
        with self.assertRaises(IntegrityError):
            GitRepo.objects.create(url='https://github.com/my-org/project')
