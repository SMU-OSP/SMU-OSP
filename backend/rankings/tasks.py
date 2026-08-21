from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from celery import shared_task
from django.conf import settings

from .services import calculate_project_rankings, replace_project_rankings


def _one_year_before(target_date: date) -> date:
    try:
        return target_date.replace(year=target_date.year - 1)
    except ValueError:
        return target_date.replace(year=target_date.year - 1, day=28)


@shared_task
def calculate_daily_project_rankings(
    period_end: str | None = None,
) -> int:
    """지정일 또는 서비스 기준 전날의 프로젝트 랭킹을 계산한다.

    Args:
        period_end: ISO 8601 형식의 집계 종료일. 없으면 서비스 날짜의 전날.

    Returns:
        DB에 저장한 프로젝트 랭킹 결과 수.
    """
    target_date = (
        date.fromisoformat(period_end)
        if period_end
        else datetime.now(ZoneInfo(settings.CELERY_TIMEZONE)).date()
        - timedelta(days=1)
    )
    results = calculate_project_rankings(
        _one_year_before(target_date),
        target_date,
    )
    replace_project_rankings(results)
    return len(results)
