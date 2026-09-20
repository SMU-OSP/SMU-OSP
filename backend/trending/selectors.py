from datetime import date, datetime

from django.db.models import Subquery, Sum

from projects.models import RepositoryLanguage

from .constants import TRENDING_REPOSITORY_LIMIT
from .models import TrendingRepository, TrendingRepositorySelection


def list_repository_languages_by_usage() -> list[str]:
    """Repository 언어를 bytes 합계 내림차순으로 조회한다."""
    language_totals = (
        RepositoryLanguage.objects.values("language")
        .annotate(total_bytes=Sum("bytes"))
        .order_by("-total_bytes", "language")
    )
    return [item["language"] for item in language_totals]


def has_successful_selection(week_start: date) -> bool:
    """해당 주의 정상 수집 완료 여부를 반환한다."""
    return TrendingRepositorySelection.objects.filter(
        week_start=week_start
    ).exists()


def list_recent_github_ids(selected_after: datetime) -> set[int]:
    """기준 시각 이후 노출된 GitHub Repository ID를 반환한다."""
    return set(
        TrendingRepository.objects.filter(
            selection__created_at__gte=selected_after
        )
        .values_list("github_id", flat=True)
    )


def list_trending_repositories() -> list[TrendingRepository]:
    """가장 최근 선정에 포함된 Repository를 순위대로 조회한다."""
    latest_selection = (
        TrendingRepositorySelection.objects.order_by("-week_start")
        .values("pk")[:1]
    )
    return list(
        TrendingRepository.objects.filter(
            selection_id=Subquery(latest_selection),
        ).order_by("position", "github_id")[:TRENDING_REPOSITORY_LIMIT]
    )
