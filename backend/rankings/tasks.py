from datetime import date, datetime
from zoneinfo import ZoneInfo

from celery import shared_task
from django.conf import settings

from .services import calculate_project_rankings


@shared_task
def calculate_daily_project_rankings(period_end: str | None = None) -> int:
    """지정일 또는 서비스 기준 오늘의 프로젝트 랭킹을 계산한다.

    Args:
        period_end: ISO 8601 형식의 집계 종료일. 없으면 현재 서비스 날짜.

    Returns:
        저장된 랭킹 실행 ID.
    """
    target_date = (
        date.fromisoformat(period_end)
        if period_end
        else datetime.now(ZoneInfo(settings.CELERY_TIMEZONE)).date()
    )
    return calculate_project_rankings(target_date).pk
