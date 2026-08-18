from datetime import UTC, date, datetime
from unittest.mock import call, patch

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from users.github_client import (
    GitHubUserClientError,
    GitHubUserContributions,
    GitHubUserSummary,
    fetch_user_contributions,
    fetch_user_summary,
)
from users.models import UserActivity
from users.services import initialize_user_activity, save_daily_activity
from users.tasks import daily_update, update_user_activity


class GitHubUserClientTests(TestCase):
    @patch("users.github_client.requests.post")
    def test_fetches_user_summary(self, post):
        post.return_value.json.return_value = {
            "data": {
                "user": {
                    "createdAt": "2020-01-02T03:04:05Z",
                    "repositories": {
                        "nodes": [
                            {"stargazerCount": 2},
                            {"stargazerCount": 3},
                        ]
                    },
                }
            }
        }

        summary = fetch_user_summary("activity-test")

        self.assertEqual(
            summary.account_created_at,
            datetime(2020, 1, 2, 3, 4, 5, tzinfo=UTC),
        )
        self.assertEqual(summary.stars, 5)
        self.assertEqual(post.call_args.kwargs["timeout"], 10)

    @patch("users.github_client.requests.post")
    def test_fetches_daily_contributions(self, post):
        post.return_value.json.return_value = {
            "data": {
                "user": {
                    "contributionsCollection": {
                        "totalCommitContributions": 3,
                        "pullRequestContributions": {"totalCount": 2},
                        "issueContributionsByRepository": [
                            {"contributions": {"totalCount": 1}},
                            {"contributions": {"totalCount": 4}},
                        ],
                    }
                }
            }
        }

        contributions = fetch_user_contributions(
            "activity-test",
            date(2026, 8, 17),
        )

        self.assertEqual(contributions.commits, 3)
        self.assertEqual(contributions.pull_requests, 2)
        self.assertEqual(contributions.issues, 5)

    @patch("users.github_client.requests.post")
    def test_rejects_graphql_errors(self, post):
        post.return_value.json.return_value = {"errors": ["rate limited"]}

        with self.assertRaises(GitHubUserClientError):
            fetch_user_summary("activity-test")


class UserSignalTests(TestCase):
    @patch("users.signals.initial_process.delay")
    def test_initial_process_is_queued_after_user_commit(self, delay):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            get_user_model().objects.create_user(
                username="celery-test",
                github_email="celery-test@example.com",
                name="테스트 사용자",
                student_id=1,
                major="IT공학",
            )
            delay.assert_not_called()

        self.assertEqual(len(callbacks), 1)
        delay.assert_called_once_with("celery-test")


class UserActivityTaskTests(TestCase):
    @patch("users.tasks.update_user_activity.delay")
    def test_daily_update_queues_each_non_superuser(self, delay):
        user_model = get_user_model()
        users = [
            user_model.objects.create_user(
                username=f"activity-{index}",
                github_email=f"activity-{index}@example.com",
                name=f"활동 사용자 {index}",
                student_id=index,
                major="IT공학",
            )
            for index in (1, 2)
        ]
        user_model.objects.create_superuser(
            username="activity-admin",
            email="activity-admin@example.com",
            password="password",
            github_email="activity-admin@example.com",
            name="활동 관리자",
            student_id=3,
            major="IT공학",
        )

        daily_update()

        self.assertEqual(delay.call_count, 2)
        delay.assert_has_calls(
            [call(users[0].pk), call(users[1].pk)],
            any_order=True,
        )

    @patch("users.tasks.refresh_user_activity")
    def test_user_activity_task_delegates_to_service(self, refresh):
        update_user_activity(17)

        refresh.assert_called_once_with(17)


class UserActivityServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="activity-test",
            github_email="activity-test@example.com",
            name="활동 테스트 사용자",
            student_id=2,
            major="IT공학",
        )

    @patch("users.services.fetch_user_contributions")
    def test_saves_current_star_snapshot_with_daily_activity(self, fetch):
        fetch.return_value = GitHubUserContributions(
            commits=3,
            pull_requests=2,
            issues=0,
        )
        save_daily_activity(
            user=self.user,
            activity_date=date(2026, 8, 17),
            stars=7,
        )

        activity = UserActivity.objects.get(user=self.user)
        self.assertEqual(activity.stars, 7)
        self.assertEqual(activity.commits, 3)
        self.assertEqual(activity.prs, 2)

    @patch("users.services.fetch_user_contributions")
    def test_new_daily_activity_is_saved_with_one_write_query(self, fetch):
        fetch.return_value = GitHubUserContributions(
            commits=3,
            pull_requests=2,
            issues=0,
        )

        with CaptureQueriesContext(connection) as queries:
            save_daily_activity(
                user=self.user,
                activity_date=date(2026, 8, 17),
                stars=7,
            )

        activity_writes = [
            query["sql"]
            for query in queries.captured_queries
            if "users_useractivity" in query["sql"].lower()
            and query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE"))
        ]
        self.assertEqual(len(activity_writes), 1)
        self.assertTrue(activity_writes[0].lstrip().upper().startswith("INSERT"))

    @patch("users.services.fetch_user_contributions")
    def test_skips_existing_activity_without_calling_github(self, fetch):
        activity_date = date(2026, 8, 17)
        UserActivity.objects.create(
            user=self.user,
            activity_date=activity_date,
            stars=5,
        )

        save_daily_activity(
            user=self.user,
            activity_date=activity_date,
            stars=7,
        )

        fetch.assert_not_called()
        self.assertEqual(
            UserActivity.objects.get(user=self.user).stars,
            5,
        )

    @patch("users.services.fetch_user_contributions")
    def test_fills_unknown_stars_without_calling_github(self, fetch):
        activity_date = date(2026, 8, 17)
        UserActivity.objects.create(
            user=self.user,
            activity_date=activity_date,
            commits=3,
        )

        save_daily_activity(
            user=self.user,
            activity_date=activity_date,
            stars=7,
        )

        fetch.assert_not_called()
        activity = UserActivity.objects.get(user=self.user)
        self.assertEqual(activity.stars, 7)
        self.assertEqual(activity.commits, 3)

    @patch("users.services.fetch_user_contributions")
    def test_does_not_save_activity_when_github_returns_errors(self, fetch):
        fetch.side_effect = GitHubUserClientError("rate limited")

        with self.assertRaises(GitHubUserClientError):
            save_daily_activity(
                user=self.user,
                activity_date=date(2026, 8, 17),
                stars=7,
            )

        self.assertFalse(UserActivity.objects.filter(user=self.user).exists())

    @patch("users.services._yesterday", return_value=date(2026, 8, 17))
    @patch("users.services.fetch_user_contributions")
    @patch("users.services.fetch_user_summary")
    def test_initial_collection_resumes_after_failure(
        self,
        fetch_summary,
        fetch_contributions,
        _yesterday,
    ):
        fetch_summary.return_value = GitHubUserSummary(
            account_created_at=datetime(2026, 8, 15, tzinfo=UTC),
            stars=7,
        )
        contribution = GitHubUserContributions(
            commits=1,
            pull_requests=1,
            issues=1,
        )
        fetch_contributions.side_effect = [
            contribution,
            GitHubUserClientError("rate limited"),
        ]

        with self.assertRaises(GitHubUserClientError):
            initialize_user_activity(self.user.username)

        self.assertEqual(UserActivity.objects.filter(user=self.user).count(), 1)
        fetch_contributions.reset_mock()
        fetch_contributions.side_effect = None
        fetch_contributions.return_value = contribution

        initialize_user_activity(self.user.username)

        self.assertEqual(UserActivity.objects.filter(user=self.user).count(), 3)
        self.assertEqual(fetch_contributions.call_count, 2)
        self.user.refresh_from_db()
        self.assertEqual(self.user.stars, 7)
        self.assertEqual(self.user.commits, 3)
        self.assertEqual(self.user.prs, 3)
        self.assertEqual(self.user.issues, 3)
        self.assertEqual(self.user.score, 16)

    def test_stars_are_unknown_until_collected(self):
        activity = UserActivity.objects.create(user=self.user)

        self.assertIsNone(activity.stars)


class UserListApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        for index, score in enumerate((10, 30, 20), start=1):
            user_model.objects.create_user(
                username=f"user-{index}",
                github_email=f"user-{index}@example.com",
                name=f"사용자 {index}",
                student_id=index,
                major="IT공학",
                score=score,
            )
        user_model.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="password",
            github_email="admin@example.com",
            name="관리자",
            student_id=999,
            major="IT공학",
        )

    def test_returns_paginated_users(self):
        with self.assertNumQueries(1):
            response = self.client.get(
                "/api/v1/users/",
                {"start": 1, "limit": 1, "sort_by": "score"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(body["data"][0]["username"], "user-3")
        self.assertEqual(
            body["detail"]["pagination"],
            {
                "start": 1,
                "limit": 1,
                "count": 3,
                "currentPage": 2,
                "totalPages": 3,
                "hasPrevious": True,
                "hasNext": True,
            },
        )

    def test_defaults_to_one_hundred_users(self):
        response = self.client.get("/api/v1/users/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail"]["pagination"]["limit"], 100)
        self.assertEqual(response.json()["detail"]["pagination"]["count"], 3)

    def test_rejects_invalid_user_list_query(self):
        response = self.client.get(
            "/api/v1/users/",
            {"start": -1, "limit": 101, "sort_by": "unknown"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["status"],
            "INVALID_PAGINATION_PARAMETER",
        )
