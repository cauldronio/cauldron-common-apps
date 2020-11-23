from django.test import TestCase
from django.db import IntegrityError

from ..models import GLInstance, GLRepo

GITLAB_INSTANCE = GLInstance.objects.get(name='GitLab')


class TestBasic(TestCase):

    def test_basic(self):
        """Basic tests."""

        repo = GLRepo.objects.create(owner='owner', repo='repo',
                                     instance=GITLAB_INSTANCE)

        found = GLRepo.objects.get(owner='owner', repo='repo')
        self.assertEqual(found, repo)

    def test_unique(self):
        """Pair (owner, repo) are unique for the same instance."""

        GLRepo.objects.create(owner='owner', repo='repo',
                              instance=GITLAB_INSTANCE)
        with self.assertRaises(IntegrityError):
            GLRepo.objects.create(owner='owner', repo='repo',
                                  instance=GITLAB_INSTANCE)
