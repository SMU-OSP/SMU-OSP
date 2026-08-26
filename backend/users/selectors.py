from datetime import UTC, date, datetime, time, timedelta

from django.db.models import (
    Count,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    Window,
)
from django.db.models.functions import Coalesce
from django.db.models.query import QuerySet

from .models import SixMonthUserRanking, User, UserActivity

SORT_FIELDS = {
    "commit": "commits",
    "star": "stars",
    "pr": "prs",
    "issue": "issues",
    "score": "score",
}


def list_public_users(
    *,
    start: int,
    limit: int,
    sort_by: str | None,
) -> tuple[list[User], int]:
    """공개 사용자 목록의 요청 구간과 전체 건수를 조회한다.

    Args:
        start: 조회를 시작할 순번.
        limit: 반환할 최대 사용자 수.
        sort_by: 내림차순 정렬할 공개 지표.

    Returns:
        요청 구간의 사용자 목록과 전체 사용자 수.
    """
    sort_field = SORT_FIELDS.get(sort_by, "date_joined")
    users = (
        User.objects.filter(is_superuser=False)
        .only(
            "username",
            "date_joined",
            "score",
            "commits",
            "stars",
            "prs",
            "issues",
        )
        .annotate(total_count=Window(Count("pk")))
        .order_by(f"-{sort_field}", "username")
    )
    results = list(users[start : start + limit])
    if results:
        return results, results[0].total_count
    if start == 0:
        return results, 0
    return results, User.objects.filter(is_superuser=False).count()


def get_public_user_profile(*, username: str) -> User:
    """6개월 랭킹 지표와 함께 공개 사용자 프로필을 조회한다."""
    return User.objects.select_related("six_month_ranking").get(
        username=username,
    )


def _user_ranking_targets(
    period_start: date,
    period_end: date,
) -> QuerySet[User]:
    """집계 기간의 사용자 활동 지표를 포함한 QuerySet을 구성한다."""
    activity_in_period = Q(
        activities__activity_date__gte=period_start,
        activities__activity_date__lte=period_end,
    )
    latest_stars = (
        UserActivity.objects.filter(
            user_id=OuterRef("pk"),
            activity_date__lte=period_end,
            stars__isnull=False,
        )
        .order_by("-activity_date", "-pk")
        .values("stars")[:1]
    )
    return (
        User.objects.filter(is_superuser=False)
        .only(
            "id",
            "username",
            "date_joined",
        )
        .annotate(
            ranking_stars=Coalesce(
                Subquery(latest_stars, output_field=IntegerField()),
                Value(0),
            ),
            ranking_commits=Coalesce(
                Sum("activities__commits", filter=activity_in_period),
                Value(0),
            ),
            ranking_prs=Coalesce(
                Sum("activities__prs", filter=activity_in_period),
                Value(0),
            ),
            ranking_issues=Coalesce(
                Sum("activities__issues", filter=activity_in_period),
                Value(0),
            ),
        )
        .order_by("username")
    )


def list_user_ranking_targets(
    period_start: date,
    period_end: date,
) -> list[User]:
    """집계 종료일까지 가입한 사용자의 기간별 활동 지표를 조회한다."""
    period_end_exclusive = datetime.combine(
        period_end + timedelta(days=1),
        time.min,
        tzinfo=UTC,
    )
    return list(
        _user_ranking_targets(period_start, period_end).filter(
            date_joined__lt=period_end_exclusive,
        )
    )


def get_user_ranking_target(
    *,
    user_id: int,
    period_start: date,
    period_end: date,
) -> User:
    """특정 사용자의 기간별 활동 지표를 가입일과 무관하게 조회한다."""
    return _user_ranking_targets(period_start, period_end).get(pk=user_id)


def list_six_month_user_ranking_cache(
    *,
    start: int,
    limit: int,
) -> tuple[list[SixMonthUserRanking], int]:
    """6개월 사용자 랭킹 캐시를 점수순으로 페이지 조회한다."""
    rankings = (
        SixMonthUserRanking.objects.select_related("user")
        .only(
            "user_id",
            "user__username",
            "user__date_joined",
            "total_score",
            "stars",
            "commits",
            "pull_requests",
            "issues",
        )
        .annotate(total_count=Window(Count("user_id")))
        .order_by("-total_score", "user__username", "user_id")
    )
    results = list(rankings[start : start + limit])
    if results:
        return results, results[0].total_count
    if start == 0:
        return results, 0
    return results, SixMonthUserRanking.objects.count()
