from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured

from projects.models import Project

from .selectors import list_project_ranking_targets

SCORE_QUANTUM = Decimal("0.01")
WEIGHT_DEFAULT = Decimal("1.00")
PROJECT_RANKING_CACHE_KEY = "rankings:projects:latest"


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


@dataclass(frozen=True)
class ProjectRankingEntry:
    """캐시에 저장하고 API로 제공할 프로젝트 랭킹 한 행."""

    rank: int
    project_id: int
    project_name: str
    total_score: Decimal
    stars: int
    forks: int
    commits: int
    pull_requests: int


def _configured_weights() -> ProjectRankingWeights:
    try:
        weights = ProjectRankingWeights(
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
    stars = end_snapshot.stars - baseline.stars
    forks = end_snapshot.forks - baseline.forks
    commits = end_snapshot.commits - baseline.commits
    pull_requests = end_snapshot.pull_requests - baseline.pull_requests
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
                project_name=item.project.name,
                total_score=item.total_score,
                stars=item.stars,
                forks=item.forks,
                commits=item.commits,
                pull_requests=item.pull_requests,
            )
        )
    return results


def cache_project_rankings(results: list[ProjectRankingEntry]) -> None:
    """마지막 정상 프로젝트 랭킹 캐시를 원자적으로 교체한다."""
    cache.set(PROJECT_RANKING_CACHE_KEY, results, timeout=None)


def get_cached_project_rankings(
    *,
    start: int,
    limit: int,
) -> tuple[list[ProjectRankingEntry], int]:
    """캐시된 최신 프로젝트 랭킹에서 요청 구간을 반환한다."""
    rankings = cache.get(PROJECT_RANKING_CACHE_KEY) or []
    return rankings[start : start + limit], len(rankings)
