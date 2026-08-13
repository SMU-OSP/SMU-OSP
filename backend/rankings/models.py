from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

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
    active_days = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=WEIGHT_DEFAULT,
        validators=WEIGHT_VALIDATORS,
    )
    max_streak = models.DecimalField(
        max_digits=20,
        decimal_places=2,
        default=WEIGHT_DEFAULT,
        validators=WEIGHT_VALIDATORS,
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return "프로젝트 랭킹 가중치"


class ProjectRankingRun(models.Model):
    """한 번 성공한 프로젝트 랭킹 계산과 당시 가중치."""

    period_start = models.DateField()
    period_end = models.DateField()
    calculated_at = models.DateTimeField(auto_now_add=True)
    stars_weight = models.DecimalField(max_digits=20, decimal_places=2)
    forks_weight = models.DecimalField(max_digits=20, decimal_places=2)
    commits_weight = models.DecimalField(max_digits=20, decimal_places=2)
    pull_requests_weight = models.DecimalField(
        max_digits=20,
        decimal_places=2,
    )
    active_days_weight = models.DecimalField(max_digits=20, decimal_places=2)
    max_streak_weight = models.DecimalField(max_digits=20, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.period_end} 프로젝트 랭킹"


class ProjectRankingResult(models.Model):
    """특정 계산 실행에서 확정된 프로젝트별 랭킹 결과."""

    run = models.ForeignKey(
        ProjectRankingRun,
        on_delete=models.CASCADE,
        related_name="results",
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="ranking_results",
    )
    rank = models.PositiveIntegerField()
    total_score = models.DecimalField(max_digits=30, decimal_places=2)
    stars = models.BigIntegerField()
    forks = models.BigIntegerField()
    commits = models.BigIntegerField()
    pull_requests = models.BigIntegerField()
    active_days = models.PositiveIntegerField()
    max_streak = models.PositiveIntegerField()
    current_streak = models.PositiveIntegerField()
    actual_period_start = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("run", "project"),
                name="ranking_run_project_uniq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.rank}위 {self.project.name}"
