from django.test import TestCase
from django.db import IntegrityError

from ..models import GHInstance, GHRepo

GITHUB_INSTANCE = GHInstance.objects.get(name='GitHub')


class TestBasic(TestCase):

    def test_basic(self):
        """Basic tests."""

        repo = GHRepo.objects.create(owner='owner', repo='repo',
                                     instance=GITHUB_INSTANCE)

        found = GHRepo.objects.get(owner='owner', repo='repo')
        self.assertEqual(found, repo)

    def test_unique(self):
        """Pair (owner, repo) are unique for the same instance."""

        GHRepo.objects.create(owner='owner', repo='repo',
                              instance=GITHUB_INSTANCE)
        with self.assertRaises(IntegrityError):
            GHRepo.objects.create(owner='owner', repo='repo',
                                  instance=GITHUB_INSTANCE)
