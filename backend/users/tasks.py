from celery import shared_task

from users.models import User
from users.services import initialize_user_activity, refresh_user_activity


@shared_task
def daily_update():
    users = User.objects.all().filter(is_superuser=False)

    for user in users:
        refresh_user_activity(user)


@shared_task
def initial_process(username: str) -> None:
    """신규 사용자의 GitHub 활동을 초기 수집한다."""
    initialize_user_activity(username)
