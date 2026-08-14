from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from common.models import CommonModel

WEIGHT_DEFAULT = Decimal("1.00")
WEIGHT_VALIDATORS = (MinValueValidator(Decimal("0.00")),)


class ProjectRankingWeight(models.Model):
    """프로젝트 랭킹 계산에 적용할 현재 지표별 가중치."""

    id = models.PositiveSmallIntegerField(
        primary_key=True,
        default=1,
        editable=False,
    )
    stars = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=WEIGHT_DEFAULT,
        validators=WEIGHT_VALIDATORS,
    )
    forks = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=WEIGHT_DEFAULT,
        validators=WEIGHT_VALIDATORS,
    )
    commits = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=WEIGHT_DEFAULT,
        validators=WEIGHT_VALIDATORS,
    )
    pull_requests = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=WEIGHT_DEFAULT,
        validators=WEIGHT_VALIDATORS,
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return "프로젝트 랭킹 가중치"


class ProjectRanking(CommonModel):
    """프로젝트별 마지막 정상 랭킹 결과."""

    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="ranking",
    )
    rank = models.PositiveIntegerField()
    total_score = models.DecimalField(max_digits=30, decimal_places=2)
    stars = models.PositiveIntegerField(default=0)
    forks = models.PositiveIntegerField(default=0)
    commits = models.PositiveIntegerField(default=0)
    pull_requests = models.PositiveIntegerField(default=0)
    stars_weight = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=WEIGHT_DEFAULT,
    )
    forks_weight = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=WEIGHT_DEFAULT,
    )
    commits_weight = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=WEIGHT_DEFAULT,
    )
    pull_requests_weight = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=WEIGHT_DEFAULT,
    )
    period_start = models.DateField()
    period_end = models.DateField()

    class Meta:
        ordering = ("rank", "project__name", "project_id")
