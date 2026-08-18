from datetime import UTC, date, datetime, timedelta

from django.db.models import Sum

from users.github_client import (
    GitHubUserContributions,
    fetch_user_contributions,
    fetch_user_summary,
)
from users.models import User, UserActivity

INITIAL_ACTIVITY_DAYS = 100


def _yesterday() -> date:
    return (datetime.now(UTC) - timedelta(days=1)).date()


def _store_activity(
    *,
    user: User,
    activity_date: date,
    contributions: GitHubUserContributions,
    stars: int | None,
) -> None:
    activity, created = UserActivity.objects.get_or_create(
        user=user,
        activity_date=activity_date,
        defaults={
            "stars": stars,
            "commits": contributions.commits,
            "prs": contributions.pull_requests,
            "issues": contributions.issues,
        },
    )
    if not created and activity.stars is None:
        UserActivity.objects.filter(pk=activity.pk).update(stars=stars)


def save_daily_activity(
    *,
    user: User,
    activity_date: date,
    stars: int,
) -> None:
    """하루의 GitHub 기여도와 누적 Star를 중복 없이 저장한다."""
    existing = (
        UserActivity.objects.filter(
            user=user,
            activity_date=activity_date,
        )
        .only("stars")
        .first()
    )
    if existing is not None:
        if existing.stars is None:
            UserActivity.objects.filter(pk=existing.pk).update(stars=stars)
        return

    contributions = fetch_user_contributions(user.username, activity_date)
    _store_activity(
        user=user,
        activity_date=activity_date,
        contributions=contributions,
        stars=stars,
    )


def _update_user_totals(user: User, stars: int) -> None:
    period_start = _yesterday() - timedelta(days=364)
    totals = UserActivity.objects.filter(
        user=user,
        activity_date__gte=period_start,
    ).aggregate(
        commits=Sum("commits"),
        prs=Sum("prs"),
        issues=Sum("issues"),
    )
    commits = totals["commits"] or 0
    prs = totals["prs"] or 0
    issues = totals["issues"] or 0
    user.stars = stars
    user.commits = commits
    user.prs = prs
    user.issues = issues
    user.score = stars + commits + prs + issues
    user.save(
        update_fields=(
            "stars",
            "commits",
            "prs",
            "issues",
            "score",
        )
    )


def _save_previous_activities(
    *,
    user: User,
    account_created_at: date,
    period_end: date,
) -> None:
    period_start = max(
        account_created_at,
        period_end - timedelta(days=INITIAL_ACTIVITY_DAYS - 1),
    )
    existing_dates = set(
        UserActivity.objects.filter(
            user=user,
            activity_date__gte=period_start,
            activity_date__lte=period_end,
        ).values_list("activity_date", flat=True)
    )
    activity_date = period_end
    while activity_date >= period_start:
        if activity_date not in existing_dates:
            contributions = fetch_user_contributions(
                user.username,
                activity_date,
            )
            _store_activity(
                user=user,
                activity_date=activity_date,
                contributions=contributions,
                stars=None,
            )
        activity_date -= timedelta(days=1)


def refresh_user_activity(user: User) -> None:
    """사용자의 전날 활동을 수집하고 최근 1년 합계를 갱신한다."""
    summary = fetch_user_summary(user.username)
    save_daily_activity(
        user=user,
        activity_date=_yesterday(),
        stars=summary.stars,
    )
    _update_user_totals(user, summary.stars)


def initialize_user_activity(username: str) -> None:
    """신규 사용자의 최대 100일 활동과 현재 합계를 초기화한다."""
    user = User.objects.get(username=username)
    summary = fetch_user_summary(username)
    _save_previous_activities(
        user=user,
        account_created_at=summary.account_created_at.date(),
        period_end=_yesterday(),
    )
    _update_user_totals(user, summary.stars)
