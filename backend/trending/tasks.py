from datetime import datetime
from zoneinfo import ZoneInfo

from celery import shared_task
from django.conf import settings

from .services import collect_trending_repositories


@shared_task
def collect_daily_trending_repositories() -> int:
    """이번 주 성공 결과가 없을 때 트렌딩 Repository를 수집한다."""
    collected_at = datetime.now(ZoneInfo(settings.CELERY_TIMEZONE))
    return collect_trending_repositories(collected_at=collected_at)
