from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from users.models import UserActivity
from users.tasks import save_yesterday_contributions


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


class UserActivityStarSnapshotTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="activity-test",
            github_email="activity-test@example.com",
            name="활동 테스트 사용자",
            student_id=2,
            major="IT공학",
        )

    @patch("users.tasks.requests.post")
    def test_saves_star_snapshot_with_yesterday_activity(self, post):
        post.return_value.json.return_value = {
            "data": {
                "user": {
                    "contributionsCollection": {
                        "totalCommitContributions": 3,
                        "pullRequestContributions": {"totalCount": 2},
                        "issueContributionsByRepository": [
                            {"contributions": {"totalCount": 1}},
                        ],
                    }
                }
            }
        }

        save_yesterday_contributions(self.user, stars=7)

        activity = UserActivity.objects.get(user=self.user)
        self.assertEqual(activity.stars, 7)
        self.assertEqual(activity.commits, 3)
        self.assertEqual(activity.prs, 2)
        self.assertEqual(activity.issues, 1)

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
