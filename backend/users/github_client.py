from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import cast

import requests
from django.conf import settings

GITHUB_API_URL = "https://api.github.com/graphql"


class GitHubUserClientError(Exception):
    """GitHub 사용자 활동을 정상적으로 조회할 수 없는 경우."""


@dataclass(frozen=True)
class GitHubUserSummary:
    """사용자 GitHub 계정 생성 시각과 공개 Repository 누적 Star."""

    account_created_at: datetime
    stars: int


@dataclass(frozen=True)
class GitHubUserContributions:
    """지정한 하루의 사용자 GitHub 기여도."""

    commits: int
    pull_requests: int
    issues: int


def _post_graphql(query: str) -> dict[str, object]:
    try:
        response = requests.post(
            GITHUB_API_URL,
            json={"query": query},
            headers={
                "Authorization": f"Bearer {settings.GH_PAT}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise GitHubUserClientError("GitHub API 요청에 실패했습니다.") from exc
    if not isinstance(payload, dict) or payload.get("errors"):
        raise GitHubUserClientError("GitHub API 응답에 오류가 있습니다.")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise GitHubUserClientError("GitHub API 응답 형식이 올바르지 않습니다.")
    return cast(dict[str, object], data)


def _user_data(data: dict[str, object]) -> dict[str, object]:
    user = data.get("user")
    if not isinstance(user, dict):
        raise GitHubUserClientError("GitHub 사용자를 찾을 수 없습니다.")
    return cast(dict[str, object], user)


def fetch_user_summary(username: str) -> GitHubUserSummary:
    """GitHub 계정 생성 시각과 공개 Repository 누적 Star를 조회한다."""
    data = _post_graphql(
        f"""
        {{
            user(login: "{username}") {{
                createdAt
                repositories(affiliations: OWNER, privacy: PUBLIC, first: 10) {{
                    nodes {{
                        stargazerCount
                    }}
                }}
            }}
        }}
        """
    )
    user = _user_data(data)
    created_at = user.get("createdAt")
    repositories = user.get("repositories")
    if not isinstance(created_at, str) or not isinstance(repositories, dict):
        raise GitHubUserClientError(
            "GitHub 사용자 응답 형식이 올바르지 않습니다."
        )
    nodes = repositories.get("nodes")
    if not isinstance(nodes, list):
        raise GitHubUserClientError(
            "GitHub Repository 응답 형식이 올바르지 않습니다."
        )
    stars = 0
    for node in nodes:
        if not isinstance(node, dict):
            raise GitHubUserClientError(
                "GitHub Repository 응답 형식이 올바르지 않습니다."
            )
        count = node.get("stargazerCount")
        if type(count) is not int or count < 0:
            raise GitHubUserClientError(
                "GitHub Star 응답 형식이 올바르지 않습니다."
            )
        stars += count
    try:
        account_created_at = datetime.fromisoformat(
            created_at.replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise GitHubUserClientError(
            "GitHub 계정 생성일 형식이 올바르지 않습니다."
        ) from exc
    return GitHubUserSummary(
        account_created_at=account_created_at,
        stars=stars,
    )


def fetch_user_contributions(
    username: str,
    activity_date: date,
) -> GitHubUserContributions:
    """지정한 날짜의 commit, PR, Issue 기여도를 조회한다."""
    from_date = datetime.combine(activity_date, time.min, tzinfo=UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    to_date = datetime.combine(activity_date, time.max, tzinfo=UTC).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    data = _post_graphql(
        f"""
        {{
            user(login: "{username}") {{
                contributionsCollection(from: "{from_date}", to: "{to_date}") {{
                    totalCommitContributions
                    pullRequestContributions {{
                        totalCount
                    }}
                    issueContributionsByRepository {{
                        contributions {{
                            totalCount
                        }}
                    }}
                }}
            }}
        }}
        """
    )
    contributions = _user_data(data).get("contributionsCollection")
    if not isinstance(contributions, dict):
        raise GitHubUserClientError(
            "GitHub 기여도 응답 형식이 올바르지 않습니다."
        )
    commits = contributions.get("totalCommitContributions")
    pull_requests = contributions.get("pullRequestContributions")
    issue_repositories = contributions.get("issueContributionsByRepository")
    if (
        type(commits) is not int
        or commits < 0
        or not isinstance(pull_requests, dict)
        or not isinstance(issue_repositories, list)
    ):
        raise GitHubUserClientError(
            "GitHub 기여도 응답 형식이 올바르지 않습니다."
        )
    pull_request_count = pull_requests.get("totalCount")
    if type(pull_request_count) is not int or pull_request_count < 0:
        raise GitHubUserClientError("GitHub PR 응답 형식이 올바르지 않습니다.")
    issue_count = 0
    for repository in issue_repositories:
        repository_contributions = (
            repository.get("contributions")
            if isinstance(repository, dict)
            else None
        )
        count = (
            repository_contributions.get("totalCount")
            if isinstance(repository_contributions, dict)
            else None
        )
        if type(count) is not int or count < 0:
            raise GitHubUserClientError(
                "GitHub Issue 응답 형식이 올바르지 않습니다."
            )
        issue_count += count
    return GitHubUserContributions(
        commits=commits,
        pull_requests=pull_request_count,
        issues=issue_count,
    )
