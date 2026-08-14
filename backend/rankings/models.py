from django.db import models


class ProjectRankingRun(models.Model):
    """한 번 성공한 프로젝트 랭킹 계산."""

    period_start = models.DateField()
    period_end = models.DateField()
    calculated_at = models.DateTimeField(auto_now_add=True)
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
