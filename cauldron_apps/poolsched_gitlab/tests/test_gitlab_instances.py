from django.test import TestCase
from django.db import IntegrityError

from ..models import GLInstance

GITLAB_INSTANCE = GLInstance.objects.get(name='GitLab')


class TestBasic(TestCase):

    def test_basic(self):
        """Basic tests"""
        instance = GLInstance.objects.get(name='GitLab')
        self.assertEqual(instance.endpoint, GITLAB_INSTANCE.endpoint)

    def test_add_one(self):
        """Add a new instance"""
        instance = GLInstance.objects.create(name='GitLab A',
                                             endpoint='https://api.gla.com')

        self.assertEqual(GLInstance.objects.count(), 2)
        found = GLInstance.objects.get(name='GitLab A')
        self.assertEqual(found, instance)

    def test_unique(self):
        """GLInstance name is unique"""

        instance = GLInstance.objects.create(name='GitLab A',
                                             endpoint='https://api.gla.com')
        with self.assertRaises(IntegrityError):
            instance = GLInstance.objects.create(name='GitLab A',
                                                 endpoint='https://api.gla.com')
