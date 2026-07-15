from urllib.parse import urlparse

import requests
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import Repository


class GitHubRepositoryError(Exception):
    def __init__(self, code, message, http_status):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


def parse_github_url(repository_url):
    parsed = urlparse(repository_url)
    host = parsed.netloc.lower()
    if host not in {"github.com", "www.github.com"}:
        raise GitHubRepositoryError(
            "INVALID_GITHUB_URL",
            "올바른 GitHub Repository URL을 입력해주세요.",
            400,
        )

    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) < 2:
        raise GitHubRepositoryError(
            "INVALID_GITHUB_URL",
            "GitHub Repository URL은 owner/repository 형식이어야 합니다.",
            400,
        )

    owner = parts[0]
    repo = parts[1].removesuffix(".git")
    if not owner or not repo:
        raise GitHubRepositoryError(
            "INVALID_GITHUB_URL",
            "GitHub Repository URL은 owner/repository 형식이어야 합니다.",
            400,
        )

    return owner, repo


def fetch_repository_metadata(repository_url):
    owner, repo = parse_github_url(repository_url)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    github_token = getattr(settings, "GH_PAT", "")
    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    try:
        response = requests.get(
            f"https://api.github.com/repos/{owner}/{repo}",
            headers=headers,
            timeout=5,
        )
    except requests.RequestException as exc:
        raise GitHubRepositoryError(
            "INTERNAL_SERVER_ERROR",
            "GitHub Repository 정보를 조회하지 못했습니다.",
            500,
        ) from exc

    if response.status_code == 404:
        raise GitHubRepositoryError(
            "GITHUB_REPOSITORY_NOT_FOUND",
            "존재하지 않는 GitHub Repository입니다.",
            404,
        )

    if response.status_code == 403:
        if response.headers.get("X-RateLimit-Remaining") == "0":
            raise GitHubRepositoryError(
                "GITHUB_RATE_LIMIT_EXCEEDED",
                "GitHub API 요청 제한이 발생했습니다. 잠시 후 다시 시도해주세요.",
                429,
            )
        raise GitHubRepositoryError(
            "PRIVATE_REPOSITORY",
            "private repository이거나 조회 권한이 없습니다.",
            403,
        )

    if response.status_code >= 400:
        raise GitHubRepositoryError(
            "INTERNAL_SERVER_ERROR",
            "GitHub Repository 정보를 조회하지 못했습니다.",
            500,
        )

    data = response.json()
    return {
        "github_id": data.get("id"),
        "name": data.get("name") or repo,
        "full_name": data.get("full_name") or f"{owner}/{repo}",
        "description": data.get("description"),
        "stars": data.get("stargazers_count") or 0,
        "forks": data.get("forks_count") or 0,
        "language": data.get("language"),
        "topics": data.get("topics") or [],
        "html_url": data.get("html_url") or repository_url,
        "github_updated_at": parse_datetime(data.get("updated_at") or ""),
        "fetched_at": timezone.now(),
        "refresh_status": Repository.RefreshStatus.SUCCESS,
        "last_error_code": None,
    }


def upsert_repository_from_url(repository_url):
    metadata = fetch_repository_metadata(repository_url)
    github_id = metadata.get("github_id")

    if github_id:
        repository, _ = Repository.objects.update_or_create(
            github_id=github_id,
            defaults=metadata,
        )
        return repository

    repository, _ = Repository.objects.update_or_create(
        html_url=metadata["html_url"],
        defaults=metadata,
    )
    return repository
