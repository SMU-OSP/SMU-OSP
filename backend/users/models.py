import math
from datetime import timedelta

from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

from common.models import CommonModel


# Triangular growth: xp_for_level(n) = 5n(n+1) → L1=10, L2=30, L3=60, L4=100, L5=150...
LEVEL_GROWTH_COEF = 5


def xp_for_level(level: int) -> int:
    if level <= 0:
        return 0
    return LEVEL_GROWTH_COEF * level * (level + 1)


def compute_level(xp: float) -> int:
    if xp is None or xp <= 0:
        return 0
    # solve LEVEL_GROWTH_COEF * n*(n+1) ≤ xp for largest integer n
    return int(math.floor((-1 + math.sqrt(1 + 4 * xp / LEVEL_GROWTH_COEF)) / 2))


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

        XPHistory.objects.update_or_create(
            user=self,
            recorded_date=timezone.localdate(),
            defaults={"xp_value": self.score},
        )

    @property
    def xp(self) -> float:
        return self.score or 0.0

    @property
    def level(self) -> int:
        return compute_level(self.xp)

    @property
    def xp_at_current_level(self) -> int:
        return xp_for_level(self.level)

    @property
    def xp_at_next_level(self) -> int:
        return xp_for_level(self.level + 1)

    @property
    def xp_to_next_level(self) -> float:
        return max(0.0, self.xp_at_next_level - self.xp)

    @property
    def xp_progress_percent(self) -> float:
        span = self.xp_at_next_level - self.xp_at_current_level
        if span <= 0:
            return 0.0
        return round(((self.xp - self.xp_at_current_level) / span) * 100, 1)


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


class XPHistory(CommonModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="xp_history")
    recorded_date = models.DateField()
    xp_value = models.FloatField(default=0.0)

    class Meta:
        unique_together = ("user", "recorded_date")
        ordering = ("-recorded_date",)
        verbose_name_plural = "XP Histories"

    def __str__(self):
        return f"{self.user} - {self.recorded_date}: {self.xp_value}"
