from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):

    github_id = models.CharField(
        max_length=100,
        default=""
    )

    github_email = models.CharField(
        max_length=100,
        default=""
    )

    major = models.CharField(
        max_length=100,
        default=""
    )