from datetime import date

from django.db.models import Exists, OuterRef, Prefetch, Q, Subquery
from django.db.models.functions import Coalesce

from projects.models import Project, RepositorySnapshot, RepositoryStatus

from .models import ProjectRankingResult, ProjectRankingRun


def has_pending_project_ranking_refreshes() -> bool:
    """랭킹 대상 프로젝트 중 아직 수집 중인 Repository가 있는지 확인한다."""
    return RepositoryStatus.objects.filter(
        repository__project__status=Project.Status.ACTIVE,
        last_status_code="PENDING",
    ).exists()


def list_project_ranking_targets(
    period_start: date,
    period_end: date,
) -> list[Project]:
    """집계 기간과 시작 경계 스냅샷이 있는 랭킹 대상을 조회한다.

    Args:
        period_start: 랭킹 집계 시작일.
        period_end: 랭킹 집계 종료일.

    Returns:
        Repository와 기간 내 스냅샷이 미리 조회된 ACTIVE 프로젝트 목록.
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
        Project.objects.filter(status=Project.Status.ACTIVE)
        .alias(
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


def get_latest_project_rankings() -> list[ProjectRankingResult]:
    """마지막 정상 프로젝트 랭킹 결과를 반환한다.

    Returns:
        프로젝트명 순서가 보장된 마지막 계산 결과. 계산 이력이 없으면 빈
        목록을 반환한다.
    """
    latest_run_id = ProjectRankingRun.objects.order_by(
        "-calculated_at",
        "-pk",
    ).values("pk")[:1]
    return list(
        ProjectRankingResult.objects.filter(run_id=Subquery(latest_run_id))
        .select_related("project")
        .only(
            "rank",
            "project_id",
            "project__name",
            "total_score",
            "stars",
            "forks",
            "commits",
            "pull_requests",
        )
        .order_by("rank", "project__name", "project_id")
    )
