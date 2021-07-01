from django.db import models


class RepositoryMetrics(models.Model):
    name = models.CharField(max_length=255)

    last_update = models.DateTimeField(auto_now=True)

    commits = models.IntegerField(default=0)
    commits_authors = models.IntegerField(default=0)
    issues = models.IntegerField(default=0)
    issues_submitters = models.IntegerField(default=0)
    reviews = models.IntegerField(default=0)
    reviews_submitters = models.IntegerField(default=0)
