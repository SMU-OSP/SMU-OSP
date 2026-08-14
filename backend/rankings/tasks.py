from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from celery import shared_task
from django.conf import settings

from .selectors import has_pending_project_ranking_refreshes
from .services import cache_project_rankings, calculate_project_rankings

RANKING_RETRY_DELAY_SECONDS = 10 * 60
RANKING_MAX_RETRIES = 12


@shared_task(bind=True, max_retries=RANKING_MAX_RETRIES)
def calculate_daily_project_rankings(
    self: Any,
    period_end: str | None = None,
) -> int:
    """지정일 또는 서비스 기준 오늘의 프로젝트 랭킹을 계산한다.

    Args:
        self: 재시도를 제어하는 Celery task 인스턴스.
        period_end: ISO 8601 형식의 집계 종료일. 없으면 현재 서비스 날짜.

    Returns:
        캐시에 저장한 프로젝트 랭킹 결과 수.
    """
    target_date = (
        date.fromisoformat(period_end)
        if period_end
        else datetime.now(ZoneInfo(settings.CELERY_TIMEZONE)).date()
    )
    if has_pending_project_ranking_refreshes():
        raise self.retry(countdown=RANKING_RETRY_DELAY_SECONDS)
    results = calculate_project_rankings(target_date)
    cache_project_rankings(results)
    return len(results)
