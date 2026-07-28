import logging
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import requests
from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import (
    Project,
    Repository,
    RepositoryLanguage,
    RepositorySnapshot,
    RepositoryStatus,
)

SUCCESS = "SUCCESS"
PENDING = "PENDING"
GITHUB_REPOSITORY_UNAVAILABLE = "GITHUB_REPOSITORY_UNAVAILABLE"
GITHUB_RATE_LIMIT_EXCEEDED = "GITHUB_RATE_LIMIT_EXCEEDED"
GITHUB_API_FAILED = "GITHUB_API_FAILED"
REFRESH_QUEUE_FAILED = "REFRESH_QUEUE_FAILED"
PENDING_TIMEOUT = timedelta(minutes=15)
logger = logging.getLogger(__name__)


class GitHubCollectionError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _dispatch_repository_refresh(repository_id, snapshot_date=None):
    try:
        if snapshot_date is None:
            refresh_repository.delay(repository_id)
        else:
            refresh_repository.delay(repository_id, snapshot_date)
    except Exception:
        logger.exception(
            "Failed to enqueue repository refresh for repository %s",
            repository_id,
        )
        _mark_collection_failed(repository_id, REFRESH_QUEUE_FAILED)


def enqueue_repository_refresh(repository_id, snapshot_date=None):
    with transaction.atomic():
        try:
            repository = Repository.objects.select_for_update().get(
                pk=repository_id
            )
        except Repository.DoesNotExist:
            return False

        status, created = RepositoryStatus.objects.get_or_create(
            repository=repository,
            defaults={"last_status_code": PENDING},
        )
        if (
            not created
            and status.last_status_code == PENDING
            and status.updated_at > timezone.now() - PENDING_TIMEOUT
        ):
            return False
        if not created:
            status.last_status_code = PENDING
            status.save(update_fields=("last_status_code", "updated_at"))

        transaction.on_commit(
            lambda: _dispatch_repository_refresh(repository_id, snapshot_date),
            robust=True,
        )
    return True


def _github_headers():
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = getattr(settings, "GH_PAT", "")
    if token and not token.startswith("dummy"):
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _github_get(path, *, params=None, empty_on_conflict=False):
    api_base_url = getattr(
        settings,
        "GITHUB_API_BASE_URL",
        "https://api.github.com",
    )
    try:
        response = requests.get(
            f"{api_base_url}{path}",
            headers=_github_headers(),
            params=params,
            timeout=10,
        )
    except requests.RequestException as error:
        raise GitHubCollectionError(GITHUB_API_FAILED) from error

    if response.status_code == 409 and empty_on_conflict:
        return []
    if response.status_code in {404, 451}:
        raise GitHubCollectionError(GITHUB_REPOSITORY_UNAVAILABLE)
    if response.status_code == 429 or (
        response.status_code == 403
        and response.headers.get("X-RateLimit-Remaining") == "0"
    ):
        raise GitHubCollectionError(GITHUB_RATE_LIMIT_EXCEEDED)
    if response.status_code >= 400:
        raise GitHubCollectionError(GITHUB_API_FAILED)

    try:
        return response.json()
    except ValueError as error:
        raise GitHubCollectionError(GITHUB_API_FAILED) from error


def _collection_window(snapshot_date):
    local_timezone = ZoneInfo(settings.CELERY_TIMEZONE)
    start_date = snapshot_date - timedelta(days=1)
    start = datetime.combine(start_date, time.min, local_timezone)
    end = datetime.combine(snapshot_date, time.min, local_timezone)
    return start.isoformat(), (end - timedelta(microseconds=1)).isoformat()


def _collect_commits(full_name, default_branch, since, until):
    shas = set()
    page = 1
    while True:
        data = _github_get(
            f"/repos/{full_name}/commits",
            params={
                "sha": default_branch,
                "since": since,
                "until": until,
                "per_page": 100,
                "page": page,
            },
            empty_on_conflict=True,
        )
        if not isinstance(data, list):
            raise GitHubCollectionError(GITHUB_API_FAILED)

        if any(
            not isinstance(item, dict)
            or not isinstance(item.get("sha"), str)
            for item in data
        ):
            raise GitHubCollectionError(GITHUB_API_FAILED)
        shas.update(item["sha"] for item in data)
        if len(data) < 100:
            return len(shas)
        page += 1


def _collect_repository(repository, snapshot_date, is_first_collection):
    metadata = _github_get(f"/repos/{repository.full_name}")
    if (
        not isinstance(metadata, dict)
        or metadata.get("private") is True
        or metadata.get("id") != repository.github_id
    ):
        raise GitHubCollectionError(GITHUB_REPOSITORY_UNAVAILABLE)

    required_strings = ("name", "full_name", "html_url", "default_branch")
    if any(not isinstance(metadata.get(field), str) for field in required_strings):
        raise GitHubCollectionError(GITHUB_API_FAILED)
    if any(
        type(metadata.get(field)) is not int or metadata[field] < 0
        for field in ("stargazers_count", "forks_count")
    ):
        raise GitHubCollectionError(GITHUB_API_FAILED)

    languages = _github_get(f"/repos/{repository.full_name}/languages")
    if not isinstance(languages, dict) or any(
        not isinstance(language, str)
        or type(byte_count) is not int
        or byte_count < 0
        for language, byte_count in languages.items()
    ):
        raise GitHubCollectionError(GITHUB_API_FAILED)

    since, until = _collection_window(snapshot_date)
    commits = _collect_commits(
        repository.full_name,
        metadata["default_branch"],
        since,
        until,
    )
    has_commit_history = None
    if is_first_collection:
        commit_history = _github_get(
            f"/repos/{repository.full_name}/commits",
            params={
                "sha": metadata["default_branch"],
                "per_page": 1,
            },
            empty_on_conflict=True,
        )
        if not isinstance(commit_history, list) or any(
            not isinstance(item, dict)
            or not isinstance(item.get("sha"), str)
            for item in commit_history
        ):
            raise GitHubCollectionError(GITHUB_API_FAILED)
        has_commit_history = bool(commit_history)

    pull_requests = _github_get(
        "/search/issues",
        params={
            "q": (
                f"repo:{repository.full_name} is:pr "
                f"created:{since}..{until}"
            ),
            "per_page": 1,
        },
    )
    if (
        not isinstance(pull_requests, dict)
        or type(pull_requests.get("total_count")) is not int
        or pull_requests["total_count"] < 0
        or type(pull_requests.get("incomplete_results")) is not bool
        or pull_requests["incomplete_results"]
    ):
        raise GitHubCollectionError(GITHUB_API_FAILED)

    return {
        "metadata": metadata,
        "languages": languages,
        "commits": commits,
        "has_commit_history": has_commit_history,
        "pull_requests": pull_requests["total_count"],
    }


def _calculate_streaks(repository):
    current_streak = 0
    max_streak = 0
    previous_date = None

    for snapshot_date, has_code_changed in repository.snapshots.order_by(
        "date"
    ).values_list("date", "has_code_changed"):
        if (
            has_code_changed
            and (
                previous_date is None
                or snapshot_date == previous_date + timedelta(days=1)
            )
        ):
            current_streak += 1
        elif has_code_changed:
            current_streak = 1
        else:
            current_streak = 0
        max_streak = max(max_streak, current_streak)
        previous_date = snapshot_date

    return current_streak, max_streak


def _save_collection(repository_id, snapshot_date, collection):
    with transaction.atomic():
        repository = (
            Repository.objects.select_for_update()
            .select_related("project")
            .get(pk=repository_id)
        )
        metadata = collection["metadata"]
        if repository.github_id != metadata["id"]:
            raise GitHubCollectionError(GITHUB_REPOSITORY_UNAVAILABLE)

        previous_languages = dict(
            repository.languages.values_list("language", "bytes")
        )
        existing_snapshot = repository.snapshots.filter(
            date=snapshot_date
        ).first()
        if existing_snapshot:
            has_code_changed = (
                existing_snapshot.has_code_changed
                or previous_languages != collection["languages"]
            )
        elif repository.snapshots.exists():
            has_code_changed = previous_languages != collection["languages"]
        else:
            has_code_changed = collection["has_commit_history"]

        repository.name = metadata["name"]
        repository.full_name = metadata["full_name"]
        repository.html_url = metadata["html_url"]
        repository.save(
            update_fields=("name", "full_name", "html_url", "updated_at")
        )

        RepositorySnapshot.objects.update_or_create(
            repository=repository,
            date=snapshot_date,
            defaults={
                "stars": metadata["stargazers_count"],
                "forks": metadata["forks_count"],
                "commits": collection["commits"],
                "pull_requests": collection["pull_requests"],
                "has_code_changed": has_code_changed,
            },
        )

        repository.languages.exclude(
            language__in=collection["languages"]
        ).delete()
        for language, byte_count in collection["languages"].items():
            RepositoryLanguage.objects.update_or_create(
                repository=repository,
                language=language,
                defaults={"bytes": byte_count},
            )

        current_streak, max_streak = _calculate_streaks(repository)
        description = metadata.get("description")
        RepositoryStatus.objects.update_or_create(
            repository=repository,
            defaults={
                "description": (
                    description if isinstance(description, str) else None
                ),
                "last_status_code": SUCCESS,
                "current_streak": current_streak,
                "max_streak": max_streak,
                "fetched_at": timezone.now(),
            },
        )
        repository.project.deactivate_if_repository_inactive(snapshot_date)


def _mark_collection_failed(repository_id, error_code):
    try:
        repository = Repository.objects.get(pk=repository_id)
    except Repository.DoesNotExist:
        return
    RepositoryStatus.objects.update_or_create(
        repository=repository,
        defaults={"last_status_code": error_code},
    )


@shared_task
def enqueue_daily_repository_refreshes(snapshot_date=None):
    target_date = (
        date.fromisoformat(snapshot_date)
        if snapshot_date
        else datetime.now(ZoneInfo(settings.CELERY_TIMEZONE)).date()
    )
    repository_ids = list(
        Repository.objects.filter(project__status=Project.Status.ACTIVE)
        .exclude(snapshots__date=target_date)
        .values_list("pk", flat=True)
    )
    return sum(
        enqueue_repository_refresh(repository_id, target_date.isoformat())
        for repository_id in repository_ids
    )


@shared_task(rate_limit=settings.REPOSITORY_REFRESH_TASK_RATE_LIMIT)
def refresh_repository(repository_id, snapshot_date=None):
    try:
        repository = Repository.objects.select_related("project").get(
            pk=repository_id
        )
    except Repository.DoesNotExist:
        return False
    if repository.project.status in {
        Project.Status.FINISHED,
        Project.Status.DELETED,
    }:
        return False

    target_date = (
        date.fromisoformat(snapshot_date)
        if snapshot_date
        else datetime.now(ZoneInfo(settings.CELERY_TIMEZONE)).date()
    )
    try:
        collection = _collect_repository(
            repository,
            target_date,
            is_first_collection=not repository.snapshots.exists(),
        )
        _save_collection(repository_id, target_date, collection)
    except Repository.DoesNotExist:
        return False
    except GitHubCollectionError as error:
        _mark_collection_failed(repository_id, error.code)
        return False
    return True
