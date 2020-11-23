from django.test import TestCase
from django.db import IntegrityError

from ..models import GHInstance

GITHUB_INSTANCE = GHInstance.objects.get(name='GitHub')


class TestBasic(TestCase):

    def test_basic(self):
        """Basic tests"""
        instance = GHInstance.objects.get(name='GitHub')
        self.assertEqual(instance.endpoint, GITHUB_INSTANCE.endpoint)

    def test_add_one(self):
        """Add a new instance"""
        instance = GHInstance.objects.create(name='GitHub A',
                                             endpoint='https://api.gha.com')

        self.assertEqual(GHInstance.objects.count(), 2)
        found = GHInstance.objects.get(name='GitHub A')
        self.assertEqual(found, instance)

    def test_unique(self):
        """GHInstance name is unique"""

        instance = GHInstance.objects.create(name='GitHub A',
                                             endpoint='https://api.gha.com')
        with self.assertRaises(IntegrityError):
            instance = GHInstance.objects.create(name='GitHub A',
                                                 endpoint='https://api.gha.com')
