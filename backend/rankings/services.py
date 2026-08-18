from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction

from projects.models import Project

from .models import ProjectRanking
from .selectors import list_project_ranking_targets

SCORE_QUANTUM = Decimal("0.01")


@dataclass(frozen=True)
class ProjectRankingWeights:
    """프로젝트 랭킹 계산에 적용할 지표별 가중치."""

    stars: Decimal
    forks: Decimal
    commits: Decimal
    pull_requests: Decimal

    @classmethod
    def from_settings(cls) -> "ProjectRankingWeights":
        """환경 설정에서 유효한 프로젝트 랭킹 가중치를 생성한다.

        Returns:
            환경 설정값으로 생성한 프로젝트 랭킹 가중치.

        Raises:
            ImproperlyConfigured: 가중치가 숫자가 아니거나 음수인 경우.
        """
        try:
            weights = cls(
                stars=Decimal(settings.PROJECT_RANKING_STARS_WEIGHT),
                forks=Decimal(settings.PROJECT_RANKING_FORKS_WEIGHT),
                commits=Decimal(settings.PROJECT_RANKING_COMMITS_WEIGHT),
                pull_requests=Decimal(
                    settings.PROJECT_RANKING_PULL_REQUESTS_WEIGHT
                ),
            )
        except (InvalidOperation, TypeError) as exc:
            raise ImproperlyConfigured(
                "프로젝트 랭킹 가중치는 숫자여야 합니다."
            ) from exc
        if min(
            weights.stars,
            weights.forks,
            weights.commits,
            weights.pull_requests,
        ) < 0:
            raise ImproperlyConfigured(
                "프로젝트 랭킹 가중치는 0 이상이어야 합니다."
            )
        return weights


@dataclass(frozen=True)
class ProjectRankingMetrics:
    """한 프로젝트의 4대 랭킹 지표와 총점."""

    project: Project
    stars: int
    forks: int
    commits: int
    pull_requests: int
    total_score: Decimal
    period_start: date

    @classmethod
    def from_project(
        cls,
        project: Project,
        *,
        period_start: date,
        weights: ProjectRankingWeights,
    ) -> "ProjectRankingMetrics":
        """프로젝트 스냅샷으로 랭킹 지표를 계산한다."""
        snapshots = project.repository.ranking_snapshots
        first_snapshot = snapshots[0]
        end_snapshot = snapshots[-1]
        baseline = next(
            (
                snapshot
                for snapshot in reversed(snapshots)
                if snapshot.date <= period_start
            ),
            first_snapshot,
        )
        stars = max(end_snapshot.stars - baseline.stars, 0)
        forks = max(end_snapshot.forks - baseline.forks, 0)
        commits = max(end_snapshot.commits - baseline.commits, 0)
        pull_requests = max(
            end_snapshot.pull_requests - baseline.pull_requests,
            0,
        )
        total_score = sum(
            (
                Decimal(stars) * weights.stars,
                Decimal(forks) * weights.forks,
                Decimal(commits) * weights.commits,
                Decimal(pull_requests) * weights.pull_requests,
            ),
            start=Decimal("0.00"),
        ).quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)
        return cls(
            project=project,
            stars=stars,
            forks=forks,
            commits=commits,
            pull_requests=pull_requests,
            total_score=total_score,
            period_start=baseline.date,
        )


def _one_year_before(target_date: date) -> date:
    try:
        return target_date.replace(year=target_date.year - 1)
    except ValueError:
        return target_date.replace(year=target_date.year - 1, day=28)


def calculate_project_rankings(period_end: date) -> list[ProjectRanking]:
    """최근 1년 프로젝트 랭킹을 계산한다.

    Args:
        period_end: 랭킹 집계 종료일.

    Returns:
        순위와 프로젝트별 지표가 확정된 랭킹 목록.
    """
    period_start = _one_year_before(period_end)
    weights = ProjectRankingWeights.from_settings()
    projects = list_project_ranking_targets(period_start, period_end)
    metrics = [
        ProjectRankingMetrics.from_project(
            project,
            period_start=period_start,
            weights=weights,
        )
        for project in projects
    ]
    metrics.sort(
        key=lambda item: (
            -item.total_score,
            item.project.name,
            item.project.pk,
        )
    )

    results = []
    previous_score = None
    current_rank = 0
    for position, item in enumerate(metrics, start=1):
        if item.total_score != previous_score:
            current_rank = position
            previous_score = item.total_score
        results.append(
            ProjectRanking(
                rank=current_rank,
                project_id=item.project.pk,
                total_score=item.total_score,
                stars=item.stars,
                forks=item.forks,
                commits=item.commits,
                pull_requests=item.pull_requests,
                period_start=item.period_start,
                period_end=period_end,
            )
        )
    return results


@transaction.atomic
def replace_project_rankings(results: list[ProjectRanking]) -> None:
    """마지막 정상 프로젝트 랭킹을 한 번에 교체한다."""
    ProjectRanking.objects.all().delete()
    ProjectRanking.objects.bulk_create(results)
