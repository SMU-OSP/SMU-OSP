from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    
    name = models.CharField(
        max_length=100,
        default="",
    )

    student_id = models.IntegerField()

    github_id = models.CharField(
        max_length=100,
        default=""
    )

    github_email = models.EmailField(blank=True)

    major = models.CharField(
        max_length=100,
        default=""
    )