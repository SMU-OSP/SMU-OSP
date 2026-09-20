from dataclasses import dataclass

import requests
from django.conf import settings


class GitHubSearchError(Exception):
    """GitHub Repository 검색 실패."""


@dataclass(frozen=True)
class TrendingRepositoryCandidate:
    """GitHub 검색 결과에서 선정에 필요한 Repository 정보."""

    github_id: int
    full_name: str
    html_url: str
    description: str | None
    language: str
    stars: int
    forks: int

    @classmethod
    def from_data(
        cls,
        data: object,
        *,
        requested_language: str,
    ) -> "TrendingRepositoryCandidate":
        """GitHub 검색 항목을 검증해 선정 후보로 변환한다.

        GitHub가 language를 null로 반환하면 검색에 사용한 언어를 적용한다.
        정수 필드는 bool을 허용하지 않고 정확한 int 값만 허용한다.

        Raises:
            GitHubSearchError: 필수 필드가 없거나 형식이 잘못된 경우.
        """
        if not isinstance(data, dict):
            raise GitHubSearchError(
                "GitHub 검색 응답 형식이 올바르지 않습니다."
            )
        github_id = data.get("id")
        full_name = data.get("full_name")
        html_url = data.get("html_url")
        description = data.get("description")
        language = data.get("language")
        stars = data.get("stargazers_count")
        forks = data.get("forks_count")
        if (
            type(github_id) is not int
            or not isinstance(full_name, str)
            or not full_name
            or not isinstance(html_url, str)
            or not html_url
        ):
            raise GitHubSearchError(
                "GitHub 검색 응답 형식이 올바르지 않습니다."
            )
        if (
            description is not None
            and not isinstance(description, str)
        ) or (
            language is not None
            and not isinstance(language, str)
        ):
            raise GitHubSearchError(
                "GitHub 검색 응답 형식이 올바르지 않습니다."
            )
        # bool은 int의 하위 타입이므로 수치 필드는 정확한 int만 허용한다.
        if (
            type(stars) is not int
            or stars < 0
            or type(forks) is not int
            or forks < 0
        ):
            raise GitHubSearchError(
                "GitHub 검색 응답 형식이 올바르지 않습니다."
            )
        return cls(
            github_id=github_id,
            full_name=full_name,
            html_url=html_url,
            description=description,
            language=language or requested_language,
            stars=stars,
            forks=forks,
        )


@dataclass(frozen=True)
class TrendingRepositorySearchPage:
    """Repository 검색 한 페이지와 다음 페이지 존재 여부."""

    repositories: tuple[TrendingRepositoryCandidate, ...]
    has_next: bool

    @classmethod
    def from_data(
        cls,
        data: object,
        *,
        requested_language: str,
        page: int,
        per_page: int,
    ) -> "TrendingRepositorySearchPage":
        """GitHub 검색 응답을 검증해 검색 페이지로 변환한다.

        Raises:
            GitHubSearchError: 검색 결과가 불완전하거나 형식이 잘못된 경우.
        """
        if not isinstance(data, dict):
            raise GitHubSearchError(
                "GitHub 검색 응답 형식이 올바르지 않습니다."
            )
        total_count = data.get("total_count")
        incomplete_results = data.get("incomplete_results")
        items = data.get("items")
        if (
            type(total_count) is not int
            or total_count < 0
            or incomplete_results is not False
            or not isinstance(items, list)
        ):
            raise GitHubSearchError(
                "GitHub 검색 결과가 완전하지 않습니다."
            )
        repositories = tuple(
            TrendingRepositoryCandidate.from_data(
                item,
                requested_language=requested_language,
            )
            for item in items
        )
        searchable_count = min(total_count, 1000)
        return cls(
            repositories=repositories,
            has_next=page * per_page < searchable_count,
        )


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = getattr(settings, "GH_PAT", "")
    if token and not token.startswith("dummy"):
        headers["Authorization"] = f"Bearer {token}"
    return headers


def search_trending_repositories(
    *,
    language: str,
    created_after: str,
    page: int,
    per_page: int,
) -> TrendingRepositorySearchPage:
    """조건에 맞는 공개 Repository를 Star 내림차순으로 조회한다.

    GitHub Search API가 제공하는 최대 1,000건 범위에서 다음 페이지
    존재 여부를 계산하며, 불완전한 검색 결과는 성공으로 처리하지 않는다.

    Raises:
        GitHubSearchError: 요청 또는 응답 검증에 실패한 경우.
    """
    api_base_url = getattr(
        settings,
        "GITHUB_API_BASE_URL",
        "https://api.github.com",
    )
    try:
        response = requests.get(
            f"{api_base_url}/search/repositories",
            headers=_headers(),
            params={
                "q": (
                    f"created:>={created_after} stars:>=1000 "
                    f'language:"{language}" is:public'
                ),
                "sort": "stars",
                "order": "desc",
                "page": page,
                "per_page": per_page,
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        raise GitHubSearchError("GitHub 검색 요청에 실패했습니다.") from exc
    if response.status_code >= 400:
        raise GitHubSearchError(
            f"GitHub 검색 요청이 실패했습니다: {response.status_code}"
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise GitHubSearchError(
            "GitHub 검색 응답을 해석하지 못했습니다."
        ) from exc
    return TrendingRepositorySearchPage.from_data(
        data,
        requested_language=language,
        page=page,
        per_page=per_page,
    )
