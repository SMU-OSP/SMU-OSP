from urllib.parse import urlparse

import requests
from django.conf import settings
from django.db import IntegrityError

from .models import Project, Repository
from .tasks import enqueue_repository_refresh

REPOSITORY_ALREADY_LINKED_MESSAGE = (
    "이미 다른 프로젝트에 연결된 Repository입니다."
)
REPOSITORY_CHANGE_NOT_ALLOWED_MESSAGE = (
    "이미 등록된 Repository는 변경하거나 연결 해제할 수 없습니다."
)
REPOSITORY_INVALID_MESSAGE = (
    "존재하는 공개 GitHub Repository URL을 입력해주세요."
)
REPOSITORY_LOOKUP_FAILED_MESSAGE = (
    "GitHub Repository 정보를 불러오지 못했습니다. 잠시 후 다시 시도해주세요."
)
REPOSITORY_SAVE_FAILED_MESSAGE = (
    "Repository를 등록하지 못했습니다. 잠시 후 다시 시도해주세요."
)


class RepositoryRegistrationError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def _parse_repository_identity(repository_url):
    parsed = urlparse(repository_url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if (
        parsed.hostname not in {"github.com", "www.github.com"}
        or len(path_parts) != 2
    ):
        raise RepositoryRegistrationError(
            "INVALID_GITHUB_URL",
            REPOSITORY_INVALID_MESSAGE,
        )
    return "/".join(path_parts).removesuffix(".git")


def _get_repository_data(full_name):
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = getattr(settings, "GH_PAT", "")
    if token and not token.startswith("dummy"):
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.get(
            f"https://api.github.com/repos/{full_name}",
            headers=headers,
            timeout=10,
        )
    except requests.RequestException as error:
        raise RepositoryRegistrationError(
            "GITHUB_API_FAILED",
            REPOSITORY_LOOKUP_FAILED_MESSAGE,
        ) from error

    if response.status_code == 404:
        raise RepositoryRegistrationError(
            "GITHUB_REPOSITORY_NOT_FOUND",
            REPOSITORY_INVALID_MESSAGE,
        )
    if response.status_code == 429 or (
        response.status_code == 403
        and response.headers.get("X-RateLimit-Remaining") == "0"
    ):
        raise RepositoryRegistrationError(
            "GITHUB_RATE_LIMIT_EXCEEDED",
            REPOSITORY_LOOKUP_FAILED_MESSAGE,
        )
    if response.status_code == 403:
        raise RepositoryRegistrationError(
            "PRIVATE_REPOSITORY",
            REPOSITORY_INVALID_MESSAGE,
        )
    if response.status_code >= 400:
        raise RepositoryRegistrationError(
            "GITHUB_API_FAILED",
            REPOSITORY_LOOKUP_FAILED_MESSAGE,
        )

    try:
        data = response.json()
    except ValueError as error:
        raise RepositoryRegistrationError(
            "GITHUB_API_FAILED",
            REPOSITORY_LOOKUP_FAILED_MESSAGE,
        ) from error

    if (
        not isinstance(data, dict)
        or not isinstance(data.get("id"), int)
        or not data.get("name")
        or not data.get("full_name")
        or not data.get("html_url")
    ):
        raise RepositoryRegistrationError(
            "GITHUB_API_FAILED",
            REPOSITORY_LOOKUP_FAILED_MESSAGE,
        )
    if data.get("private") is True:
        raise RepositoryRegistrationError(
            "PRIVATE_REPOSITORY",
            REPOSITORY_INVALID_MESSAGE,
        )
    return data


def prepare_repository_registration(repository_url):
    full_name = _parse_repository_identity(repository_url)
    if Repository.objects.filter(full_name__iexact=full_name).exists():
        raise ValueError(REPOSITORY_ALREADY_LINKED_MESSAGE)

    data = _get_repository_data(full_name)
    if Repository.objects.filter(github_id=data["id"]).exists():
        raise ValueError(REPOSITORY_ALREADY_LINKED_MESSAGE)
    return data


def prepare_project_repository_update(project, repository_url):
    repository = getattr(project, "repository", None)
    if repository is not None:
        if repository_url != repository.html_url:
            raise ValueError(REPOSITORY_CHANGE_NOT_ALLOWED_MESSAGE)
        return None
    if not repository_url:
        return None
    return prepare_repository_registration(repository_url)


def update_project_repository(
    project,
    repository_url,
    *,
    previous_project_status=None,
    repository_data=None,
):
    repository = getattr(project, "repository", None)
    if repository:
        if repository_url != repository.html_url:
            raise ValueError(REPOSITORY_CHANGE_NOT_ALLOWED_MESSAGE)
        if (
            previous_project_status == project.Status.INACTIVE
            and project.status == project.Status.ACTIVE
        ):
            enqueue_repository_refresh(repository.pk)
        return
    if not repository_url:
        return

    data = repository_data or prepare_repository_registration(repository_url)
    if Repository.objects.filter(full_name__iexact=data["full_name"]).exists():
        raise ValueError(REPOSITORY_ALREADY_LINKED_MESSAGE)
    if Repository.objects.filter(github_id=data["id"]).exists():
        raise ValueError(REPOSITORY_ALREADY_LINKED_MESSAGE)

    try:
        repository = Repository.objects.create(
            project=project,
            github_id=data["id"],
            name=data["name"],
            full_name=data["full_name"],
            html_url=data["html_url"],
        )
    except IntegrityError as error:
        raise RepositoryRegistrationError(
            "INTERNAL_SERVER_ERROR",
            REPOSITORY_SAVE_FAILED_MESSAGE,
        ) from error
    enqueue_repository_refresh(repository.pk)
