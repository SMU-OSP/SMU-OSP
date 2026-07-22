import requests
from celery import shared_task
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Repository


def enqueue_repository_refresh(repository_id):
    transaction.on_commit(lambda: refresh_repository.delay(repository_id))


def normalize_description(value):
    if value is None:
        return None
    return "".join(
        character for character in value if ord(character) <= 0xFFFF
    ).strip()


def mark_refresh_failed(repository, error_code):
    repository.refresh_status = Repository.RefreshStatus.FAILED
    repository.last_error_code = error_code
    repository.save(
        update_fields=("refresh_status", "last_error_code", "updated_at")
    )


@shared_task
def refresh_repository(repository_id):
    try:
        repository = Repository.objects.get(pk=repository_id)
    except Repository.DoesNotExist:
        return False

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = getattr(settings, "GH_PAT", "")
    if token and not token.startswith("dummy"):
        headers["Authorization"] = f"Bearer {token}"

    api_base_url = getattr(
        settings,
        "GITHUB_API_BASE_URL",
        "https://api.github.com",
    )
    try:
        response = requests.get(
            f"{api_base_url}/repos/{repository.full_name}",
            headers=headers,
            timeout=10,
        )
    except requests.RequestException:
        mark_refresh_failed(repository, "GITHUB_API_FAILED")
        return False

    if response.status_code == 404:
        mark_refresh_failed(repository, "REPOSITORY_NOT_FOUND")
        return False
    if response.status_code == 403:
        mark_refresh_failed(repository, "GITHUB_RATE_LIMIT_EXCEEDED")
        return False
    if response.status_code >= 400:
        mark_refresh_failed(repository, "GITHUB_API_FAILED")
        return False

    try:
        data = response.json()
    except ValueError:
        mark_refresh_failed(repository, "GITHUB_API_FAILED")
        return False
    if not isinstance(data, dict) or data.get("private") is True:
        mark_refresh_failed(repository, "GITHUB_API_FAILED")
        return False

    repository.github_id = data.get("id")
    repository.name = data.get("name") or repository.name
    repository.full_name = data.get("full_name") or repository.full_name
    repository.description = normalize_description(data.get("description"))
    repository.stars = int(data.get("stargazers_count") or 0)
    repository.forks = int(data.get("forks_count") or 0)
    repository.language = data.get("language")
    repository.topics = list(data.get("topics") or [])
    repository.html_url = data.get("html_url") or repository.html_url
    repository.github_updated_at = parse_datetime(data.get("updated_at") or "")
    repository.fetched_at = timezone.now()
    repository.refresh_status = Repository.RefreshStatus.SUCCESS
    repository.last_error_code = None
    try:
        with transaction.atomic():
            repository.save()
    except IntegrityError:
        mark_refresh_failed(repository, "REPOSITORY_ALREADY_LINKED")
        return False
    return True
