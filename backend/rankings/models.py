from django.db import models

from common.models import CommonModel


class ProjectRanking(CommonModel):
    """프로젝트별 마지막 정상 랭킹 결과.

    stars는 집계 종료 시점의 누적 스냅샷이고, forks, commits,
    pull_requests는 집계 기간 동안의 증가량이다.
    """

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
    period_start = models.DateField()
    period_end = models.DateField()

    class Meta:
        ordering = ("rank", "project__name", "project_id")
