import requests
from datetime import datetime, timedelta, UTC

from django.conf import settings
from celery import shared_task

from users.models import User, UserActivity


GITHUB_API_URL = "https://api.github.com/graphql"

HEADERS = {
    "Authorization": f"Bearer {settings.GH_PAT}",
    "Content-Type": "application/json",
}


@shared_task
def daily_update():
    users = User.objects.all().filter(is_superuser=False)

    for user in users:
        print(f"Start User {user.username} updated")

        data = get_initial_info(user.username)

        print(data)

        stars = sum(
            repo["stargazerCount"]
            for repo in data["data"]["user"]["repositories"]["nodes"]
        )
        user.stars = stars
        user.save()

        save_yesterday_contributions(user)

        user.update_contributions()
        user.update_score()
        print(f"User {user.username} updated")

    print(f"All users updated")


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

    user.stars = stars
    user.save()
    user.update_contributions()
    user.update_score()


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
            userActivity = UserActivity.objects.create(user=user)
            userActivity.activity_date = current_date
            userActivity.commits = commits
            userActivity.prs = prs
            userActivity.issues = issues
            userActivity.save()
            print("Done")

            requests_number += 1
            current_date -= timedelta(days=1)

            if requests_number > 100:
                break

        print(f"yesterday: {yesterday}, created date: {created_at_date}")

    except Exception as e:
        print(f"An error occurred: {e}")


def save_yesterday_contributions(user):
    try:
        print("Start gathering yesterday contribution data")

        yesterday = (datetime.now(UTC) - timedelta(days=1)).date()

        current_date = yesterday

        print(f"yesterday: {yesterday}")

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

        print("Saving data start")
        userActivity = UserActivity.objects.create(
            user=user, activity_date=current_date
        )
        # userActivity.activity_date = current_date
        userActivity.commits = commits
        userActivity.prs = prs
        userActivity.issues = issues
        userActivity.save()
        print(f"{yesterday} contribution saved")

    except Exception as e:
        print(f"An error occurred: {e}")


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
