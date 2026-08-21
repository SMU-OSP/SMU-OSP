from datetime import date

from django.db.models import (
    Count,
    Exists,
    IntegerField,
    OuterRef,
    Prefetch,
    Q,
    Subquery,
    Sum,
    Value,
    Window,
)
from django.db.models.functions import Coalesce

from projects.models import Project, RepositorySnapshot
from users.models import User, UserActivity

from .models import ProjectRanking


def list_user_ranking_targets(
    period_start: date,
    period_end: date,
) -> list[User]:
    """집계 기간의 활동 합계와 종료일 누적 Star를 함께 조회한다."""
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
    return list(
        User.objects.filter(
            is_superuser=False,
            date_joined__date__lte=period_end,
        )
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


def list_project_rankings(
    *,
    start: int,
    limit: int,
) -> tuple[list[ProjectRanking], int]:
    """마지막 정상 프로젝트 랭킹의 요청 구간을 조회한다."""
    rankings = (
        ProjectRanking.objects.select_related("project")
        .only(
            "project_id",
            "project__name",
            "rank",
            "total_score",
            "stars",
            "forks",
            "commits",
            "pull_requests",
        )
        .annotate(total_count=Window(Count("project_id")))
        .order_by(
            "rank",
            "project__name",
            "project_id",
        )
    )
    results = list(rankings[start : start + limit])
    if results:
        return results, results[0].total_count
    if start == 0:
        return results, 0
    return results, ProjectRanking.objects.count()


def list_project_ranking_targets(
    period_start: date,
    period_end: date,
) -> list[Project]:
    """집계 기간과 시작 경계 스냅샷이 있는 랭킹 대상을 조회한다.

    Args:
        period_start: 랭킹 집계 시작일.
        period_end: 랭킹 집계 종료일.

    Returns:
        Repository와 기간 내 스냅샷이 미리 조회된 프로젝트 목록.
    """
    baseline_snapshot = (
        RepositorySnapshot.objects.filter(
            repository_id=OuterRef("repository_id"),
            date__lte=period_start,
        )
        .order_by("-date", "-pk")
        .values("pk")[:1]
    )
    first_period_snapshot = (
        RepositorySnapshot.objects.filter(
            repository_id=OuterRef("repository_id"),
            date__gte=period_start,
            date__lte=period_end,
        )
        .order_by("date", "pk")
        .values("pk")[:1]
    )
    latest_snapshot = (
        RepositorySnapshot.objects.filter(
            repository_id=OuterRef("repository_id"),
            date__lte=period_end,
        )
        .order_by("-date", "-pk")
        .values("pk")[:1]
    )
    available_snapshot = RepositorySnapshot.objects.filter(
        repository__project_id=OuterRef("pk"),
        date__lte=period_end,
    )
    starting_snapshot = Coalesce(
        Subquery(baseline_snapshot),
        Subquery(first_period_snapshot),
    )
    snapshots = (
        RepositorySnapshot.objects.filter(
            Q(pk=starting_snapshot)
            | Q(pk=Subquery(latest_snapshot))
        )
        .only(
            "repository_id",
            "date",
            "stars",
            "forks",
            "commits",
            "pull_requests",
        )
        .order_by("date", "pk")
    )
    return list(
        Project.objects.alias(
            has_ranking_snapshot=Exists(available_snapshot),
        )
        .filter(has_ranking_snapshot=True)
        .select_related("repository")
        .only("id", "name", "repository__id")
        .prefetch_related(
            Prefetch(
                "repository__snapshots",
                queryset=snapshots,
                to_attr="ranking_snapshots",
            )
        )
    )
