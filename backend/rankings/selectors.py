from datetime import date

from django.db.models import Prefetch

from projects.models import Project, RepositorySnapshot

from .models import ProjectRankingResult, ProjectRankingRun


def list_project_ranking_targets(period_end: date) -> list[Project]:
    """집계 종료일까지 정상 스냅샷이 있는 랭킹 대상 프로젝트를 조회한다.

    Args:
        period_end: 랭킹 집계 종료일.

    Returns:
        Repository와 기간 내 스냅샷이 미리 조회된 ACTIVE 프로젝트 목록.
    """
    snapshots = (
        RepositorySnapshot.objects.filter(date__lte=period_end)
        .only(
            "repository_id",
            "date",
            "stars",
            "forks",
            "commits",
            "pull_requests",
            "has_code_changed",
        )
        .order_by("date", "pk")
    )
    return list(
        Project.objects.filter(
            status=Project.Status.ACTIVE,
            repository__snapshots__date__lte=period_end,
        )
        .select_related("repository")
        .only("id", "name", "repository__id")
        .prefetch_related(
            Prefetch(
                "repository__snapshots",
                queryset=snapshots,
                to_attr="ranking_snapshots",
            )
        )
        .distinct()
    )


def get_latest_project_rankings() -> list[ProjectRankingResult]:
    """마지막 정상 프로젝트 랭킹 결과를 반환한다.

    Returns:
        프로젝트명 순서가 보장된 마지막 계산 결과. 계산 이력이 없으면 빈
        목록을 반환한다.
    """
    run = ProjectRankingRun.objects.order_by("-calculated_at", "-pk").first()
    if run is None:
        return []
    return list(
        run.results.select_related("project").order_by(
            "rank",
            "project__name",
            "project_id",
        )
    )
