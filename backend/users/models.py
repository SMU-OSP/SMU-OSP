from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):

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

    github_id = models.CharField(
        max_length=100,
        default="",
    )

    github_email = models.EmailField(
        null=True,
    )
