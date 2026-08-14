from django.db.models import Count, Window

from .models import User

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
