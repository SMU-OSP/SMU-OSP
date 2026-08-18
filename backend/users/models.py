from django.contrib.auth.models import AbstractUser
from django.db import models

from common.models import CommonModel


class User(AbstractUser):

    github_email = models.EmailField(
        null=False,
        blank=False,
    )

    name = models.CharField(
        max_length=100,
        null=False,
        blank=False,
    )

    student_id = models.PositiveIntegerField(
        null=False,
        blank=False,
    )

    major = models.CharField(
        max_length=100,
        null=False,
        blank=False,
    )

    commits = models.PositiveIntegerField(
        default=0,
        null=True,
    )

    stars = models.PositiveIntegerField(
        default=0,
        null=True,
    )

    prs = models.PositiveIntegerField(
        default=0,
        null=True,
    )

    issues = models.PositiveIntegerField(
        default=0,
        null=True,
    )

    score = models.FloatField(
        default=0.0,
        null=True,
    )

class UserActivity(CommonModel):
    """사용자의 일별 GitHub 활동과 누적 Star 스냅샷."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activities")
    activity_date = models.DateField(null=True)
    stars = models.PositiveIntegerField(null=True)
    commits = models.IntegerField(default=0)
    prs = models.IntegerField(default=0)
    issues = models.IntegerField(default=0)

    class Meta:
        unique_together = ("user", "activity_date")
        verbose_name_plural = "User Activities"

    def __str__(self):
        return f"{self.user} - {self.activity_date}"
