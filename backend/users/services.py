from dataclasses import dataclass
from datetime import date, timedelta

from django.db import transaction

from common.dates import (
    ONE_YEAR_RANKING_DAYS,
    SIX_MONTH_RANKING_DAYS,
    ranking_period_boundary,
)

from .models import SixMonthUserRanking, User
from .selectors import (
    get_user_ranking_target,
    list_public_users,
    list_six_month_user_ranking_cache,
    list_user_ranking_targets,
)


@dataclass(frozen=True)
class UserRankingResult:
    """사용자 랭킹 응답에 사용하는 지표와 순위."""

    user: User
    rank: int
    total_score: int
    stars: int
    commits: int
    pull_requests: int
    issues: int


def _ranking_values(user: User) -> dict[str, int]:
    stars = int(user.ranking_stars)
    commits = int(user.ranking_commits)
    pull_requests = int(user.ranking_prs)
    issues = int(user.ranking_issues)
    return {
        "total_score": stars + commits + pull_requests + issues,
        "stars": stars,
        "commits": commits,
        "pull_requests": pull_requests,
        "issues": issues,
    }


def list_saved_user_rankings(
    *,
    start: int,
    limit: int,
) -> tuple[list[UserRankingResult], int]:
    """기존 User 저장값으로 1년 사용자 랭킹을 조회한다."""
    users, count = list_public_users(
        start=start,
        limit=limit,
        sort_by="score",
    )
    results = [
        UserRankingResult(
            user=user,
            rank=rank,
            total_score=int(user.score or 0),
            stars=int(user.stars or 0),
            commits=int(user.commits or 0),
            pull_requests=int(user.prs or 0),
            issues=int(user.issues or 0),
        )
        for rank, user in enumerate(users, start=start + 1)
    ]
    return results, count


def list_six_month_user_rankings(
    *,
    start: int,
    limit: int,
) -> tuple[list[UserRankingResult], int]:
    """저장된 6개월 지표를 정렬해 사용자 랭킹을 반환한다."""
    rankings, count = list_six_month_user_ranking_cache(
        start=start,
        limit=limit,
    )
    results = [
        UserRankingResult(
            user=ranking.user,
            rank=rank,
            total_score=ranking.total_score,
            stars=ranking.stars,
            commits=ranking.commits,
            pull_requests=ranking.pull_requests,
            issues=ranking.issues,
        )
        for rank, ranking in enumerate(rankings, start=start + 1)
    ]
    return results, count


def calculate_user_rankings(
    period_start: date,
    period_end: date,
) -> list[UserRankingResult]:
    """지정 기간의 사용자 지표를 계산하고 순위를 부여한다."""
    users = list_user_ranking_targets(period_start, period_end)
    metrics = [(user, _ranking_values(user)) for user in users]
    metrics.sort(
        key=lambda item: (
            -item[1]["total_score"],
            item[0].username,
        )
    )
    return [
        UserRankingResult(user=user, rank=rank, **values)
        for rank, (user, values) in enumerate(metrics, start=1)
    ]


@transaction.atomic
def refresh_user_ranking_caches(
    *,
    user_id: int,
    period_end: date,
) -> None:
    """한 사용자의 1년·6개월 랭킹 캐시를 함께 갱신한다."""
    one_year_start = ranking_period_boundary(
        period_end, ONE_YEAR_RANKING_DAYS
    ) + timedelta(days=1)
    six_month_start = ranking_period_boundary(
        period_end, SIX_MONTH_RANKING_DAYS
    ) + timedelta(days=1)
    one_year_user = get_user_ranking_target(
        user_id=user_id,
        period_start=one_year_start,
        period_end=period_end,
    )
    six_month_user = get_user_ranking_target(
        user_id=user_id,
        period_start=six_month_start,
        period_end=period_end,
    )
    one_year_values = _ranking_values(one_year_user)
    six_month_values = _ranking_values(six_month_user)

    User.objects.filter(pk=user_id).update(
        score=one_year_values["total_score"],
        stars=one_year_values["stars"],
        commits=one_year_values["commits"],
        prs=one_year_values["pull_requests"],
        issues=one_year_values["issues"],
    )
    SixMonthUserRanking.objects.update_or_create(
        user_id=user_id,
        defaults={
            **six_month_values,
            "period_start": six_month_start,
            "period_end": period_end,
        },
    )
