from django.contrib.auth.models import AbstractUser
from django.db import models

from common.models import CommonModel

from encrypted_model_fields.fields import (
    EncryptedCharField,
    EncryptedPositiveIntegerField,
    EncryptedEmailField,
)


class User(AbstractUser):

    github_email = EncryptedEmailField(
        null=False,
        blank=False,
    )

    name = EncryptedCharField(
        max_length=100,
        null=False,
        blank=False,
    )

    student_id = EncryptedPositiveIntegerField(
        null=False,
        blank=False,
    )

    major = EncryptedCharField(
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


class SixMonthUserRanking(CommonModel):
    """사용자별 마지막 정상 6개월 랭킹 지표 캐시."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="six_month_ranking",
    )
    total_score = models.PositiveBigIntegerField(default=0)
    stars = models.PositiveIntegerField(default=0)
    commits = models.PositiveIntegerField(default=0)
    pull_requests = models.PositiveIntegerField(default=0)
    issues = models.PositiveIntegerField(default=0)
    period_start = models.DateField()
    period_end = models.DateField()
