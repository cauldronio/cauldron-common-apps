import datetime

from django.utils import timezone
from django.test import TestCase
from django.contrib.auth import get_user_model

from poolsched.models import Job
from ..models import GLToken

User = get_user_model()


class TestBasic(TestCase):

    def test_basic(self):
        """Basic tests."""
        tomorrow = timezone.now() + datetime.timedelta(days=1)
        user = User.objects.create(username='Bob')
        token = GLToken.objects.create(token='1234567890', reset=tomorrow, user=user)

        tokens = GLToken.objects.all()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0], token)

    def test_default(self):
        """Test default token attributes"""
        token_str = '1234567890'
        token = GLToken(token=token_str)
        token.save()
        job = Job.objects.create()
        token.jobs.add(job)

        self.assertEqual(token.token, token_str)
        self.assertLessEqual(token.reset, timezone.now())
        self.assertIsNone(token.user)
        self.assertEqual(token.jobs.count(), 1)
        self.assertEqual(token.jobs.first(), job)
