from datetime import UTC, date, datetime, timedelta

from celery import chain, shared_task

from common.dates import (
    ONE_YEAR_RANKING_DAYS,
    SIX_MONTH_RANKING_DAYS,
    ranking_period_boundary,
)
from users.tasks import daily_update

from .services import (
    calculate_project_rankings,
    replace_daily_project_rankings,
)


@shared_task
def calculate_daily_project_rankings(
    period_end: str | None = None,
) -> int:
    """지정일 또는 서비스 기준 전날의 프로젝트 랭킹을 계산한다.

    Args:
        period_end: ISO 8601 형식의 집계 종료일. 없으면 UTC 기준 전날.

    Returns:
        DB에 저장한 1년·6개월 프로젝트 랭킹 결과 수.
    """
    target_date = (
        date.fromisoformat(period_end)
        if period_end
        else datetime.now(UTC).date() - timedelta(days=1)
    )
    one_year_period_start = ranking_period_boundary(
        target_date, ONE_YEAR_RANKING_DAYS
    )
    six_month_period_start = ranking_period_boundary(
        target_date, SIX_MONTH_RANKING_DAYS
    )
    one_year_projects = calculate_project_rankings(
        one_year_period_start,
        target_date,
    )
    six_month_projects = calculate_project_rankings(
        six_month_period_start,
        target_date,
    )
    replace_daily_project_rankings(
        one_year_projects=one_year_projects,
        six_month_projects=six_month_projects,
    )
    return len(one_year_projects) + len(six_month_projects)


@shared_task
def refresh_users_and_calculate_rankings() -> None:
    """사용자 활동 갱신 후 일별 랭킹 계산을 순서대로 예약한다.

    한 번 정한 UTC 집계 종료일을 사용자와 프로젝트 랭킹에 동일하게 적용한다.
    """
    period_end = (
        datetime.now(UTC).date() - timedelta(days=1)
    ).isoformat()
    chain(
        daily_update.si(period_end=period_end),
        calculate_daily_project_rankings.si(period_end=period_end),
    ).apply_async()
