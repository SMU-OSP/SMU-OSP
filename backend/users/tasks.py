import logging
from datetime import UTC, date, datetime, timedelta

import requests
from celery import shared_task
from django.conf import settings

from users.models import User, UserActivity
from users.services import refresh_user_ranking_caches

GITHUB_API_URL = "https://api.github.com/graphql"

HEADERS = {
    "Authorization": f"Bearer {settings.GH_PAT}",
    "Content-Type": "application/json",
}
logger = logging.getLogger(__name__)


@shared_task
def daily_update(period_end: str | None = None) -> None:
    """UTC 집계일의 사용자 활동과 1년·6개월 캐시를 갱신한다.

    사용자 한 명의 수집 또는 저장이 실패해도 기존 캐시를 유지하고 다음
    사용자를 계속 처리한다.

    Args:
        period_end: ISO 8601 형식의 집계 종료일. 없으면 UTC 기준 전날.
    """
    users = User.objects.all().filter(is_superuser=False)
    target_date = (
        date.fromisoformat(period_end)
        if period_end
        else datetime.now(UTC).date() - timedelta(days=1)
    )

    for user in users:
        print(f"Start User {user.username} updated")

        try:
            data = get_initial_info(user.username)
            if data is None:
                logger.error(
                    "GitHub activity collection failed for user %s",
                    user.username,
                )
                continue
            stars = sum(
                repo["stargazerCount"]
                for repo in data["data"]["user"]["repositories"]["nodes"]
            )
            save_yesterday_contributions(
                user,
                stars,
                activity_date=target_date,
            )
            refresh_user_ranking_caches(
                user_id=user.pk,
                period_end=target_date,
            )
        except Exception:
            logger.exception(
                "User activity and ranking refresh failed for user %s",
                user.username,
            )
            continue

        print(data)
        print(f"User {user.username} updated")

    print("All users updated")


@shared_task
def initial_process(username):

    print("Start initial process")

    user = User.objects.get(username=username)

    data = get_initial_info(username)

    print(data)

    github_account_created_at = data["data"]["user"]["createdAt"]

    repositories = data["data"]["user"]["repositories"]["nodes"]
    stars = sum(repo["stargazerCount"] for repo in repositories)

    print(f"User GitHub account created at: {github_account_created_at}")
    print(f"Total stars: {stars}")

    save_previous_contributions(user, github_account_created_at)

    period_end = (datetime.now(UTC) - timedelta(days=1)).date()
    UserActivity.objects.update_or_create(
        user=user,
        activity_date=period_end,
        defaults={"stars": stars},
    )
    refresh_user_ranking_caches(
        user_id=user.pk,
        period_end=period_end,
    )


def get_initial_info(username):

    query = f"""
    {{
        user(login: "{username}") {{
            createdAt
            repositories(affiliations: OWNER, privacy: PUBLIC, first: 10) {{
                nodes {{
                    name
                    stargazerCount
                }}
            }}
        }}
    }}
    """
    json_data = {"query": query}

    response = requests.post(GITHUB_API_URL, json=json_data, headers=HEADERS)
    response_data = response.json()

    if "errors" in response_data:
        print(f"GitHub GraphQL API Failed: {response_data['errors']}")
    else:
        return response_data


def save_previous_contributions(user, created_at):
    try:
        print("Start gathering previous contribution data")

        created_at_date = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").date()

        yesterday = (datetime.now(UTC) - timedelta(days=1)).date()

        current_date = yesterday

        requests_number = 1

        print(f"yesterday: {yesterday}, created date: {created_at_date}")

        while current_date >= created_at_date:

            from_date = datetime.combine(current_date, datetime.min.time()).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            to_date = datetime.combine(current_date, datetime.max.time()).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )

            print(f"from: {from_date} to: {to_date}, request start")

            query = f"""
            {{
                user(login: "{user.username}") {{
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

            json_data = {"query": query}

            response = requests.post(GITHUB_API_URL, json=json_data, headers=HEADERS)
            response_data = response.json()

            if "errors" in response_data:
                print(f"GitHub GraphQL API Failed: {response_data['errors']}")
            else:
                print(response_data)
                commits, prs, issues = calculate_contributions(response_data)
                print(f"Commits: {commits}, PRs: {prs}, Issues: {issues}")

            print(f"from: {from_date} to: {to_date}, request {requests_number} times")

            print("Saving data start")
            user_activity = UserActivity.objects.create(user=user)
            user_activity.activity_date = current_date
            user_activity.commits = commits
            user_activity.prs = prs
            user_activity.issues = issues
            user_activity.save()
            print("Done")

            requests_number += 1
            current_date -= timedelta(days=1)

            if requests_number > 100:
                break

        print(f"yesterday: {yesterday}, created date: {created_at_date}")

    except Exception as e:
        print(f"An error occurred: {e}")


def save_yesterday_contributions(
    user: User,
    stars: int,
    *,
    activity_date: date,
) -> None:
    """지정한 UTC 날짜의 사용자 활동과 누적 Star를 저장한다.

    Args:
        user: 활동을 수집할 사용자.
        stars: 집계 시점에 사용자가 보유한 누적 Star 수.
        activity_date: 활동을 수집하고 저장할 UTC 날짜.

    Raises:
        requests.RequestException: GitHub 요청 또는 응답 처리에 실패한 경우.
        ValueError: GitHub GraphQL 응답에 오류가 포함된 경우.
    """
    print("Start gathering yesterday contribution data")

    print(f"yesterday: {activity_date}")

    from_date = f"{activity_date}T00:00:00Z"
    to_date = f"{activity_date}T23:59:59Z"

    print(f"from: {from_date} to: {to_date}, request start")

    query = f"""
        {{
            user(login: "{user.username}") {{
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

    json_data = {"query": query}

    response = requests.post(GITHUB_API_URL, json=json_data, headers=HEADERS)
    response.raise_for_status()
    response_data = response.json()

    if "errors" in response_data:
        raise ValueError(
            f"GitHub GraphQL API Failed: {response_data['errors']}"
        )

    print(response_data)
    commits, prs, issues = calculate_contributions(response_data)
    print(f"Commits: {commits}, PRs: {prs}, Issues: {issues}")

    print("Saving data start")
    UserActivity.objects.update_or_create(
        user=user,
        activity_date=activity_date,
        defaults={
            "stars": stars,
            "commits": commits,
            "prs": prs,
            "issues": issues,
        },
    )
    print(f"{activity_date} contribution saved")


def calculate_contributions(response):

    commits = response["data"]["user"]["contributionsCollection"][
        "totalCommitContributions"
    ]
    prs = response["data"]["user"]["contributionsCollection"][
        "pullRequestContributions"
    ]["totalCount"]
    issues = sum(
        repo["contributions"]["totalCount"]
        for repo in response["data"]["user"]["contributionsCollection"][
            "issueContributionsByRepository"
        ]
    )

    return commits, prs, issues
