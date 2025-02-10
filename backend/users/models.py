from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):

    github_email = models.EmailField(
        null=False,
        blank=False,
    )

    name = models.CharField(
        max_length=100,
        default="",
    )

    student_id = models.PositiveIntegerField(
        null=True,
    )

    major = models.CharField(
        max_length=100,
        default="",
    )

    commit = models.PositiveIntegerField(
        default=0,
        null=True,
    )

    star = models.PositiveIntegerField(
        default=0,
        null=True,
    )

    pr = models.PositiveIntegerField(
        default=0,
        null=True,
    )

    issue = models.PositiveIntegerField(
        default=0,
        null=True,
    )

    score = models.FloatField(
        default=0.0,
        null=True,
    )
