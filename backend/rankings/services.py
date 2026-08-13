from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction

from projects.models import Project

from .models import (
    ProjectRankingResult,
    ProjectRankingRun,
    ProjectRankingWeight,
)
from .selectors import list_project_ranking_targets

SCORE_QUANTUM = Decimal("0.01")


@dataclass(frozen=True)
class ProjectRankingMetrics:
    """한 프로젝트의 랭킹 계산에 필요한 기간 활동 지표."""

    project: Project
    actual_period_start: date
    stars: int
    forks: int
    commits: int
    pull_requests: int
    total_score: Decimal


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
    weights: ProjectRankingWeight,
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
    weights: ProjectRankingWeight,
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
    actual_period_start = max(period_start, first_snapshot.date)
    stars = end_snapshot.stars - baseline.stars
    forks = end_snapshot.forks - baseline.forks
    commits = end_snapshot.commits - baseline.commits
    pull_requests = end_snapshot.pull_requests - baseline.pull_requests
    return ProjectRankingMetrics(
        project=project,
        actual_period_start=actual_period_start,
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
    )


def calculate_project_rankings(period_end: date) -> ProjectRankingRun:
    """최근 1년 프로젝트 랭킹을 계산해 하나의 실행 이력으로 저장한다.

    모든 계산을 완료한 뒤 결과를 한 트랜잭션으로 저장하므로 계산 또는
    저장에 실패하면 이전의 마지막 정상 결과가 유지된다.

    Args:
        period_end: 랭킹 집계 종료일.

    Returns:
        성공적으로 저장된 랭킹 계산 실행.
    """
    period_start = _one_year_before(period_end)
    weights, _ = ProjectRankingWeight.objects.get_or_create(pk=1)
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

    with transaction.atomic():
        run = ProjectRankingRun.objects.create(
            period_start=period_start,
            period_end=period_end,
            stars_weight=weights.stars,
            forks_weight=weights.forks,
            commits_weight=weights.commits,
            pull_requests_weight=weights.pull_requests,
        )
        results = []
        previous_score = None
        current_rank = 0
        for position, item in enumerate(metrics, start=1):
            if item.total_score != previous_score:
                current_rank = position
                previous_score = item.total_score
            results.append(
                ProjectRankingResult(
                    run=run,
                    project=item.project,
                    rank=current_rank,
                    total_score=item.total_score,
                    stars=item.stars,
                    forks=item.forks,
                    commits=item.commits,
                    pull_requests=item.pull_requests,
                    actual_period_start=item.actual_period_start,
                )
            )
        ProjectRankingResult.objects.bulk_create(results)
    return run
