from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping, cast
from urllib.parse import parse_qs, urlparse

import requests
from django.conf import settings


class GitHubErrorCode(StrEnum):
    INVALID_URL = "INVALID_GITHUB_URL"
    REPOSITORY_NOT_FOUND = "GITHUB_REPOSITORY_NOT_FOUND"
    PRIVATE_REPOSITORY = "PRIVATE_REPOSITORY"
    RATE_LIMIT_EXCEEDED = "GITHUB_RATE_LIMIT_EXCEEDED"
    API_FAILED = "GITHUB_API_FAILED"


class GitHubClientError(Exception):
    def __init__(self, code: GitHubErrorCode):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class GitHubRepositoryIdentity:
    github_id: int
    name: str
    full_name: str
    html_url: str


@dataclass(frozen=True)
class GitHubRepositoryMetadata(GitHubRepositoryIdentity):
    description: str | None
    default_branch: str
    stars: int
    forks: int


@dataclass(frozen=True)
class GitHubRepositoryCollection:
    metadata: GitHubRepositoryMetadata
    languages: dict[str, int]
    commits: int
    pull_requests: int

    @property
    def has_commit_history(self) -> bool:
        return self.commits > 0


def parse_repository_url(repository_url: str) -> str:
    parsed = urlparse(repository_url)
    path_parts = [part for part in parsed.path.split("/") if part]
    if (
        parsed.hostname not in {"github.com", "www.github.com"}
        or len(path_parts) != 2
    ):
        raise GitHubClientError(GitHubErrorCode.INVALID_URL)
    return "/".join(path_parts).removesuffix(".git")


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = getattr(settings, "GH_PAT", "")
    if token and not token.startswith("dummy"):
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get_json(
    path: str,
    *,
    params: Mapping[str, str | int] | None = None,
    empty_on_conflict: bool = False,
) -> tuple[object, dict[str, object]]:
    api_base_url = getattr(
        settings,
        "GITHUB_API_BASE_URL",
        "https://api.github.com",
    )
    try:
        response = requests.get(
            f"{api_base_url}{path}",
            headers=_headers(),
            params=params,
            timeout=10,
        )
    except requests.RequestException as error:
        raise GitHubClientError(GitHubErrorCode.API_FAILED) from error

    if response.status_code == 409 and empty_on_conflict:
        return [], {}
    if response.status_code in {404, 451}:
        raise GitHubClientError(GitHubErrorCode.REPOSITORY_NOT_FOUND)
    if response.status_code == 429 or (
        response.status_code == 403
        and response.headers.get("X-RateLimit-Remaining") == "0"
    ):
        raise GitHubClientError(GitHubErrorCode.RATE_LIMIT_EXCEEDED)
    if response.status_code == 403:
        raise GitHubClientError(GitHubErrorCode.PRIVATE_REPOSITORY)
    if response.status_code >= 400:
        raise GitHubClientError(GitHubErrorCode.API_FAILED)

    try:
        data: object = response.json()
    except ValueError as error:
        raise GitHubClientError(GitHubErrorCode.API_FAILED) from error
    links = (
        cast(dict[str, object], response.links)
        if isinstance(response.links, dict)
        else {}
    )
    return data, links


def _as_object(data: object) -> dict[str, object]:
    if not isinstance(data, dict):
        raise GitHubClientError(GitHubErrorCode.API_FAILED)
    return cast(dict[str, object], data)


def _parse_identity(
    data: Mapping[str, object],
) -> GitHubRepositoryIdentity:
    if data.get("private") is True:
        raise GitHubClientError(GitHubErrorCode.PRIVATE_REPOSITORY)

    github_id = data.get("id")
    name = data.get("name")
    full_name = data.get("full_name")
    html_url = data.get("html_url")
    if (
        type(github_id) is not int
        or not isinstance(name, str)
        or not name
        or not isinstance(full_name, str)
        or not full_name
        or not isinstance(html_url, str)
        or not html_url
    ):
        raise GitHubClientError(GitHubErrorCode.API_FAILED)
    return GitHubRepositoryIdentity(
        github_id=github_id,
        name=name,
        full_name=full_name,
        html_url=html_url,
    )


def fetch_repository_identity(full_name: str) -> GitHubRepositoryIdentity:
    data, _ = _get_json(f"/repos/{full_name}")
    return _parse_identity(_as_object(data))


def _fetch_repository_metadata(full_name: str) -> GitHubRepositoryMetadata:
    raw_data, _ = _get_json(f"/repos/{full_name}")
    data = _as_object(raw_data)
    identity = _parse_identity(data)
    default_branch = data.get("default_branch")
    stars = data.get("stargazers_count")
    forks = data.get("forks_count")
    if (
        not isinstance(default_branch, str)
        or not default_branch
        or type(stars) is not int
        or stars < 0
        or type(forks) is not int
        or forks < 0
    ):
        raise GitHubClientError(GitHubErrorCode.API_FAILED)
    description = data.get("description")
    return GitHubRepositoryMetadata(
        github_id=identity.github_id,
        name=identity.name,
        full_name=identity.full_name,
        html_url=identity.html_url,
        description=description if isinstance(description, str) else None,
        default_branch=default_branch,
        stars=stars,
        forks=forks,
    )


def _fetch_languages(full_name: str) -> dict[str, int]:
    raw_data, _ = _get_json(f"/repos/{full_name}/languages")
    data = _as_object(raw_data)
    if any(
        not isinstance(language, str)
        or type(byte_count) is not int
        or byte_count < 0
        for language, byte_count in data.items()
    ):
        raise GitHubClientError(GitHubErrorCode.API_FAILED)
    return cast(dict[str, int], data)


def _fetch_commit_count(full_name: str, default_branch: str) -> int:
    data, links = _get_json(
        f"/repos/{full_name}/commits",
        params={"sha": default_branch, "per_page": 1},
        empty_on_conflict=True,
    )
    if not isinstance(data, list) or any(
        not isinstance(item, dict) or not isinstance(item.get("sha"), str)
        for item in data
    ):
        raise GitHubClientError(GitHubErrorCode.API_FAILED)
    if not data:
        return 0

    last_link = links.get("last")
    if not isinstance(last_link, dict):
        return len(data)
    last_url = last_link.get("url")
    if not isinstance(last_url, str):
        raise GitHubClientError(GitHubErrorCode.API_FAILED)
    last_pages = parse_qs(urlparse(last_url).query).get("page")
    if not last_pages or not last_pages[0].isdigit():
        raise GitHubClientError(GitHubErrorCode.API_FAILED)
    return int(last_pages[0])


def _fetch_pull_request_count(full_name: str) -> int:
    raw_data, _ = _get_json(
        "/search/issues",
        params={"q": f"repo:{full_name} is:pr", "per_page": 1},
    )
    data = _as_object(raw_data)
    total_count = data.get("total_count")
    incomplete_results = data.get("incomplete_results")
    if (
        type(total_count) is not int
        or total_count < 0
        or type(incomplete_results) is not bool
        or incomplete_results
    ):
        raise GitHubClientError(GitHubErrorCode.API_FAILED)
    return total_count


def collect_repository(
    full_name: str,
    expected_github_id: int,
) -> GitHubRepositoryCollection:
    metadata = _fetch_repository_metadata(full_name)
    if metadata.github_id != expected_github_id:
        raise GitHubClientError(GitHubErrorCode.REPOSITORY_NOT_FOUND)
    return GitHubRepositoryCollection(
        metadata=metadata,
        languages=_fetch_languages(full_name),
        commits=_fetch_commit_count(full_name, metadata.default_branch),
        pull_requests=_fetch_pull_request_count(full_name),
    )
