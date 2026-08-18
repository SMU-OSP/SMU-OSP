from celery import shared_task

from users.github_client import GitHubUserClientError
from users.models import User
from users.services import initialize_user_activity, refresh_user_activity


@shared_task
def daily_update() -> None:
    """일반 사용자별 활동 갱신 Task를 예약한다."""
    user_ids = User.objects.filter(is_superuser=False).values_list(
        "pk",
        flat=True,
    )
    for user_id in user_ids.iterator():
        update_user_activity.delay(user_id)


@shared_task(
    autoretry_for=(GitHubUserClientError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def update_user_activity(user_id: int) -> None:
    """한 사용자의 GitHub 활동을 갱신한다."""
    refresh_user_activity(user_id)


@shared_task(
    autoretry_for=(GitHubUserClientError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def initial_process(username: str) -> None:
    """신규 사용자의 GitHub 활동을 초기 수집한다."""
    initialize_user_activity(username)
