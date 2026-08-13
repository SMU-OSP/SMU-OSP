from .models import ProjectRankingResult, ProjectRankingRun


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
