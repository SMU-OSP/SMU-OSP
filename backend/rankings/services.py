from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from projects.models import Project

from .models import ProjectRanking, ProjectRankingWeight
from .selectors import list_project_ranking_targets

SCORE_QUANTUM = Decimal("0.01")
WEIGHT_DEFAULT = Decimal("1.00")


@dataclass(frozen=True)
class ProjectRankingWeights:
    """프로젝트 랭킹 계산에 적용할 지표별 가중치."""

    stars: Decimal = WEIGHT_DEFAULT
    forks: Decimal = WEIGHT_DEFAULT
    commits: Decimal = WEIGHT_DEFAULT
    pull_requests: Decimal = WEIGHT_DEFAULT


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


@dataclass(frozen=True)
class ProjectRankingEntry:
    """DB에 저장할 프로젝트 랭킹 한 행."""

    rank: int
    project_id: int
    total_score: Decimal
    stars: int
    forks: int
    commits: int
    pull_requests: int
    period_start: date
    period_end: date
    stars_weight: Decimal = WEIGHT_DEFAULT
    forks_weight: Decimal = WEIGHT_DEFAULT
    commits_weight: Decimal = WEIGHT_DEFAULT
    pull_requests_weight: Decimal = WEIGHT_DEFAULT


def _configured_weights() -> ProjectRankingWeights:
    configured, _ = ProjectRankingWeight.objects.get_or_create(pk=1)
    return ProjectRankingWeights(
        stars=configured.stars,
        forks=configured.forks,
        commits=configured.commits,
        pull_requests=configured.pull_requests,
    )


def _one_year_before(target_date: date) -> date:
    try:
        return target_date.replace(year=target_date.year - 1)
    except ValueError:
        return target_date.replace(year=target_date.year - 1, day=28)


def _score(
    *,
    stars: int,
    forks: int,
    commits: int,
    pull_requests: int,
    weights: ProjectRankingWeights,
) -> Decimal:
    return sum(
        (
            Decimal(stars) * weights.stars,
            Decimal(forks) * weights.forks,
            Decimal(commits) * weights.commits,
            Decimal(pull_requests) * weights.pull_requests,
        ),
        start=Decimal("0.00"),
    ).quantize(SCORE_QUANTUM, rounding=ROUND_HALF_UP)


def _calculate_project_metrics(
    project: Project,
    *,
    period_start: date,
    weights: ProjectRankingWeights,
) -> ProjectRankingMetrics:
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
    return ProjectRankingMetrics(
        project=project,
        stars=stars,
        forks=forks,
        commits=commits,
        pull_requests=pull_requests,
        total_score=_score(
            stars=stars,
            forks=forks,
            commits=commits,
            pull_requests=pull_requests,
            weights=weights,
        ),
        period_start=baseline.date,
    )


def calculate_project_rankings(period_end: date) -> list[ProjectRankingEntry]:
    """최근 1년 프로젝트 랭킹을 계산한다.

    Args:
        period_end: 랭킹 집계 종료일.

    Returns:
        순위와 프로젝트별 지표가 확정된 랭킹 목록.
    """
    period_start = _one_year_before(period_end)
    weights = _configured_weights()
    projects = list_project_ranking_targets(period_start, period_end)
    metrics = [
        _calculate_project_metrics(
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
            ProjectRankingEntry(
                rank=current_rank,
                project_id=item.project.pk,
                total_score=item.total_score,
                stars=item.stars,
                forks=item.forks,
                commits=item.commits,
                pull_requests=item.pull_requests,
                stars_weight=weights.stars,
                forks_weight=weights.forks,
                commits_weight=weights.commits,
                pull_requests_weight=weights.pull_requests,
                period_start=item.period_start,
                period_end=period_end,
            )
        )
    return results


@transaction.atomic
def replace_project_rankings(results: list[ProjectRankingEntry]) -> None:
    """마지막 정상 프로젝트 랭킹을 한 번에 교체한다."""
    ProjectRanking.objects.all().delete()
    ProjectRanking.objects.bulk_create(
        [
            ProjectRanking(
                project_id=result.project_id,
                rank=result.rank,
                total_score=result.total_score,
                stars=result.stars,
                forks=result.forks,
                commits=result.commits,
                pull_requests=result.pull_requests,
                stars_weight=result.stars_weight,
                forks_weight=result.forks_weight,
                commits_weight=result.commits_weight,
                pull_requests_weight=result.pull_requests_weight,
                period_start=result.period_start,
                period_end=result.period_end,
            )
            for result in results
        ]
    )
