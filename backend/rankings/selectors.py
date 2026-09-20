from datetime import date

from django.db.models import (
    Count,
    Exists,
    F,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Window,
)
from django.db.models.functions import Coalesce, RowNumber

from projects.models import Project, RepositorySnapshot

from .models import (
    ProjectRanking,
    SixMonthProjectRanking,
)


def list_project_rankings(
    *,
    start: int,
    limit: int,
) -> tuple[list[ProjectRanking], int]:
    """마지막 정상 프로젝트 랭킹의 요청 구간을 조회한다."""
    rankings = (
        ProjectRanking.objects.select_related("project")
        .only(
            "project_id",
            "project__name",
            "total_score",
            "stars",
            "forks",
            "commits",
            "pull_requests",
        )
        .annotate(
            rank=Window(
                expression=RowNumber(),
                order_by=(
                    F("total_score").desc(),
                    F("project__name").asc(),
                    F("project_id").asc(),
                ),
            ),
            total_count=Window(Count("project_id")),
        )
        .order_by(
            "-total_score",
            "project__name",
            "project_id",
        )
    )
    results = list(rankings[start : start + limit])
    if results:
        return results, results[0].total_count
    if start == 0:
        return results, 0
    return results, ProjectRanking.objects.count()


def list_six_month_project_rankings(
    *,
    start: int,
    limit: int,
) -> tuple[list[SixMonthProjectRanking], int]:
    """마지막 정상 6개월 프로젝트 랭킹의 요청 구간을 조회한다."""
    rankings = (
        SixMonthProjectRanking.objects.select_related("project")
        .only(
            "project_id",
            "project__name",
            "total_score",
            "stars",
            "forks",
            "commits",
            "pull_requests",
        )
        .annotate(
            rank=Window(
                expression=RowNumber(),
                order_by=(
                    F("total_score").desc(),
                    F("project__name").asc(),
                    F("project_id").asc(),
                ),
            ),
            total_count=Window(Count("project_id")),
        )
        .order_by("-total_score", "project__name", "project_id")
    )
    results = list(rankings[start : start + limit])
    if results:
        return results, results[0].total_count
    if start == 0:
        return results, 0
    return results, SixMonthProjectRanking.objects.count()


def list_project_ranking_targets(
    period_start: date,
    period_end: date,
) -> list[Project]:
    """집계 기간과 시작 경계 스냅샷이 있는 랭킹 대상을 조회한다.

    Args:
        period_start: 랭킹 집계 시작일.
        period_end: 랭킹 집계 종료일.

    Returns:
        Repository와 기간 내 스냅샷이 미리 조회된 프로젝트 목록.
    """
    baseline_snapshot = (
        RepositorySnapshot.objects.filter(
            repository_id=OuterRef("repository_id"),
            date__lte=period_start,
        )
        .order_by("-date", "-pk")
        .values("pk")[:1]
    )
    first_period_snapshot = (
        RepositorySnapshot.objects.filter(
            repository_id=OuterRef("repository_id"),
            date__gte=period_start,
            date__lte=period_end,
        )
        .order_by("date", "pk")
        .values("pk")[:1]
    )
    latest_snapshot = (
        RepositorySnapshot.objects.filter(
            repository_id=OuterRef("repository_id"),
            date__lte=period_end,
        )
        .order_by("-date", "-pk")
        .values("pk")[:1]
    )
    available_snapshot = RepositorySnapshot.objects.filter(
        repository__project_id=OuterRef("pk"),
        date__lte=period_end,
    )
    starting_snapshot = Coalesce(
        Subquery(baseline_snapshot),
        Subquery(first_period_snapshot),
    )
    snapshots = (
        RepositorySnapshot.objects.filter(
            Q(pk=starting_snapshot)
            | Q(pk=Subquery(latest_snapshot))
        )
        .only(
            "repository_id",
            "date",
            "stars",
            "forks",
            "commits",
            "pull_requests",
        )
        .order_by("date", "pk")
    )
    return list(
        Project.objects.alias(
            has_ranking_snapshot=Exists(available_snapshot),
        )
        .filter(has_ranking_snapshot=True)
        .select_related("repository")
        .only("id", "name", "repository__id")
        .prefetch_related(
            Prefetch(
                "repository__snapshots",
                queryset=snapshots,
                to_attr="ranking_snapshots",
            )
        )
    )
