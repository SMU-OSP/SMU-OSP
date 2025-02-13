from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

from common.models import CommonModel


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

    def update_contributions(self):
        one_year_ago = timezone.now() - timedelta(days=365)

        stats = UserActivity.objects.filter(
            user=self, activity_date__gte=one_year_ago.date()
        ).aggregate(
            total_commits=models.Sum("commits"),
            total_prs=models.Sum("prs"),
            total_issues=models.Sum("issues"),
        )

        self.commits = stats["total_commits"] or 0
        self.prs = stats["total_prs"] or 0
        self.issues = stats["total_issues"] or 0

        self.save()

    def update_score(self):

        self.score = self.stars + self.commits + self.prs + self.issues

        self.save()


class UserActivity(CommonModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activities")
    activity_date = models.DateField(null=True)
    commits = models.IntegerField(default=0)
    prs = models.IntegerField(default=0)
    issues = models.IntegerField(default=0)

    class Meta:
        unique_together = ("user", "activity_date")
        verbose_name_plural = "User Activities"

    def __str__(self):
        return f"{self.user} - {self.activity_date}"
