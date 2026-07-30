import logging
from datetime import date, datetime, timedelta
from urllib.parse import parse_qs, urlparse
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
REFRESH_SKIPPED = "REFRESH_SKIPPED"
PENDING_TIMEOUT = timedelta(minutes=15)
logger = logging.getLogger(__name__)


class GitHubCollectionError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _dispatch_repository_refresh(
    repository_id: int,
    snapshot_date: str,
    refresh_requested_at: str | None = None,
) -> None:
    try:
        refresh_repository.delay(
            repository_id,
            snapshot_date,
            refresh_requested_at,
        )
    except Exception:
        logger.exception(
            "Failed to enqueue repository refresh for repository %s",
            repository_id,
        )
        _mark_collection_failed(
            repository_id,
            REFRESH_QUEUE_FAILED,
            refresh_requested_at,
        )


def _current_snapshot_date() -> date:
    return datetime.now(ZoneInfo(settings.CELERY_TIMEZONE)).date()


def enqueue_repository_refresh(
    repository_id: int,
    snapshot_date: date | None = None,
) -> bool:
    target_date = snapshot_date or _current_snapshot_date()
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
        refresh_requested_at = status.updated_at.isoformat()

        transaction.on_commit(
            lambda: _dispatch_repository_refresh(
                repository_id,
                target_date.isoformat(),
                refresh_requested_at,
            ),
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


def _github_get(
    path,
    *,
    params=None,
    empty_on_conflict=False,
    include_links=False,
):
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
        return ([], {}) if include_links else []
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
        data = response.json()
    except ValueError as error:
        raise GitHubCollectionError(GITHUB_API_FAILED) from error
    return (data, response.links) if include_links else data


def _collect_commit_count(full_name, default_branch):
    data, links = _github_get(
        f"/repos/{full_name}/commits",
        params={"sha": default_branch, "per_page": 1},
        empty_on_conflict=True,
        include_links=True,
    )
    if not isinstance(data, list) or any(
        not isinstance(item, dict) or not isinstance(item.get("sha"), str)
        for item in data
    ):
        raise GitHubCollectionError(GITHUB_API_FAILED)
    if not data:
        return 0

    last_url = links.get("last", {}).get("url")
    if not last_url:
        return len(data)
    last_pages = parse_qs(urlparse(last_url).query).get("page")
    if not last_pages or not last_pages[0].isdigit():
        raise GitHubCollectionError(GITHUB_API_FAILED)
    return int(last_pages[0])


def _collect_repository(repository):
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

    commits = _collect_commit_count(
        repository.full_name,
        metadata["default_branch"],
    )

    pull_requests = _github_get(
        "/search/issues",
        params={
            "q": f"repo:{repository.full_name} is:pr",
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
        "has_commit_history": commits > 0,
        "pull_requests": pull_requests["total_count"],
    }


def _calculate_streaks(repository: Repository) -> tuple[int, int]:
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


def _save_collection(
    repository_id,
    snapshot_date,
    collection,
    refresh_requested_at=None,
):
    with transaction.atomic():
        project_id = Repository.objects.values_list(
            "project_id",
            flat=True,
        ).get(pk=repository_id)
        project = Project.objects.select_for_update().get(pk=project_id)
        repository = Repository.objects.select_for_update().get(
            pk=repository_id
        )
        status = None
        if refresh_requested_at is not None:
            status = (
                RepositoryStatus.objects.select_for_update()
                .filter(
                    repository=repository,
                    last_status_code=PENDING,
                    updated_at=refresh_requested_at,
                )
                .first()
            )
            if status is None:
                return False

        project.repository = repository
        if project.status != Project.Status.ACTIVE:
            if status is not None:
                status.last_status_code = REFRESH_SKIPPED
                status.save(
                    update_fields=("last_status_code", "updated_at")
                )
            return False

        metadata = collection["metadata"]
        if repository.github_id != metadata["id"]:
            raise GitHubCollectionError(GITHUB_REPOSITORY_UNAVAILABLE)

        previous_languages = dict(
            repository.languages.values_list("language", "bytes")
        )
        repository_status = status or RepositoryStatus.objects.filter(
            repository=repository
        ).first()
        stored_current_streak = (
            repository_status.current_streak if repository_status else 0
        )
        stored_max_streak = (
            repository_status.max_streak if repository_status else 0
        )
        existing_snapshot = repository.snapshots.filter(
            date=snapshot_date
        ).first()
        previous_snapshot = (
            repository.snapshots.filter(date__lt=snapshot_date)
            .order_by("-date")
            .first()
        )
        if existing_snapshot:
            has_code_changed = (
                existing_snapshot.has_code_changed
                or previous_languages != collection["languages"]
            )
        elif previous_snapshot:
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

        if (
            existing_snapshot
            and not existing_snapshot.has_code_changed
            and has_code_changed
        ):
            current_streak, max_streak = _calculate_streaks(repository)
        elif existing_snapshot:
            current_streak = stored_current_streak
            max_streak = stored_max_streak
        elif has_code_changed:
            continues_streak = (
                previous_snapshot is not None
                and previous_snapshot.has_code_changed
                and previous_snapshot.date
                == snapshot_date - timedelta(days=1)
            )
            current_streak = (
                stored_current_streak + 1 if continues_streak else 1
            )
            max_streak = max(stored_max_streak, current_streak)
        else:
            current_streak = 0
            max_streak = stored_max_streak
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
        if project.deactivate_if_repository_inactive(snapshot_date):
            project.save(update_fields=("status", "updated_at"))
        return True


def _mark_collection_failed(
    repository_id,
    error_code,
    refresh_requested_at=None,
):
    try:
        repository = Repository.objects.get(pk=repository_id)
    except Repository.DoesNotExist:
        return False
    if refresh_requested_at is not None:
        return bool(
            RepositoryStatus.objects.filter(
                repository=repository,
                last_status_code=PENDING,
                updated_at=refresh_requested_at,
            ).update(
                last_status_code=error_code,
                updated_at=timezone.now(),
            )
        )
    RepositoryStatus.objects.update_or_create(
        repository=repository,
        defaults={"last_status_code": error_code},
    )
    return True


def _mark_collection_skipped(
    repository_id,
    refresh_requested_at=None,
):
    filters = {
        "repository_id": repository_id,
        "last_status_code": PENDING,
    }
    if refresh_requested_at is not None:
        filters["updated_at"] = refresh_requested_at
    return bool(
        RepositoryStatus.objects.filter(**filters).update(
            last_status_code=REFRESH_SKIPPED,
            updated_at=timezone.now(),
        )
    )


@shared_task
def enqueue_daily_repository_refreshes(snapshot_date: str | None = None) -> int:
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
        enqueue_repository_refresh(repository_id, target_date)
        for repository_id in repository_ids
    )


@shared_task(rate_limit=settings.REPOSITORY_REFRESH_TASK_RATE_LIMIT)
def refresh_repository(
    repository_id: int,
    snapshot_date: str,
    refresh_requested_at: str | None = None,
) -> bool:
    try:
        repository = Repository.objects.select_related("project").get(
            pk=repository_id
        )
    except Repository.DoesNotExist:
        return False
    if repository.project.status != Project.Status.ACTIVE:
        _mark_collection_skipped(repository_id, refresh_requested_at)
        return False

    target_date = date.fromisoformat(snapshot_date)
    try:
        collection = _collect_repository(repository)
        return _save_collection(
            repository_id,
            target_date,
            collection,
            refresh_requested_at,
        )
    except (Project.DoesNotExist, Repository.DoesNotExist):
        return False
    except GitHubCollectionError as error:
        _mark_collection_failed(
            repository_id,
            error.code,
            refresh_requested_at,
        )
        return False
