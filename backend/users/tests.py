from datetime import UTC, date, datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from users.models import SixMonthUserRanking, UserActivity
from users.selectors import (
    get_user_ranking_target,
    list_user_ranking_targets,
)
from users.services import (
    calculate_user_rankings,
    refresh_user_ranking_caches,
)
from users.tasks import (
    daily_update,
    initial_process,
    save_yesterday_contributions,
)


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

        activity_date = date(2026, 8, 25)
        save_yesterday_contributions(
            self.user,
            stars=7,
            activity_date=activity_date,
        )

        activity = UserActivity.objects.get(user=self.user)
        self.assertEqual(activity.activity_date, activity_date)
        self.assertEqual(activity.stars, 7)
        self.assertEqual(activity.commits, 3)
        self.assertEqual(activity.prs, 2)
        self.assertEqual(activity.issues, 1)

    def test_stars_are_unknown_until_collected(self):
        activity = UserActivity.objects.create(user=self.user)

        self.assertIsNone(activity.stars)

    @patch("users.tasks.requests.post")
    def test_collection_error_does_not_save_activity(self, post):
        post.return_value.json.return_value = {
            "errors": [{"message": "GitHub API failed"}],
        }

        with self.assertRaises(ValueError):
            save_yesterday_contributions(
                self.user,
                stars=7,
                activity_date=date(2026, 8, 25),
            )

        self.assertFalse(UserActivity.objects.filter(user=self.user).exists())

    @patch("users.tasks.save_yesterday_contributions")
    @patch("users.tasks.get_initial_info")
    def test_daily_update_continues_after_user_collection_failure(
        self,
        get_initial_info,
        save_yesterday_contributions,
    ):
        successful_user = get_user_model().objects.create_user(
            username="activity-success",
            github_email="activity-success@example.com",
            name="수집 성공 사용자",
            student_id=3,
            major="IT공학",
        )
        successful_response = {
            "data": {
                "user": {
                    "repositories": {
                        "nodes": [{"stargazerCount": 7}],
                    }
                }
            }
        }
        get_initial_info.side_effect = lambda username: (
            successful_response
            if username == successful_user.username
            else None
        )

        with patch(
            "users.tasks.refresh_user_ranking_caches"
        ) as refresh_rankings:
            daily_update.run()

        save_yesterday_contributions.assert_called_once()
        self.assertEqual(
            save_yesterday_contributions.call_args.args,
            (successful_user, 7),
        )
        refresh_rankings.assert_called_once_with(
            user_id=successful_user.pk,
            period_end=save_yesterday_contributions.call_args.kwargs[
                "activity_date"
            ],
        )

    @patch("users.tasks.refresh_user_ranking_caches")
    @patch("users.tasks.save_yesterday_contributions")
    @patch("users.tasks.get_initial_info")
    def test_daily_update_skips_cache_and_continues_after_activity_save_failure(
        self,
        get_initial_info,
        save_yesterday_contributions,
        refresh_rankings,
    ):
        get_user_model().objects.create_user(
            username="activity-success",
            github_email="activity-success@example.com",
            name="활동 저장 성공 사용자",
            student_id=4,
            major="IT공학",
        )
        get_initial_info.return_value = {
            "data": {
                "user": {
                    "repositories": {
                        "nodes": [{"stargazerCount": 7}],
                    }
                }
            }
        }
        save_yesterday_contributions.side_effect = [
            RuntimeError("activity save failed"),
            None,
        ]

        daily_update.run(period_end="2026-08-25")

        self.assertEqual(save_yesterday_contributions.call_count, 2)
        successful_user = save_yesterday_contributions.call_args_list[1].args[0]
        refresh_rankings.assert_called_once_with(
            user_id=successful_user.pk,
            period_end=date(2026, 8, 25),
        )

    @patch("users.tasks.refresh_user_ranking_caches")
    @patch("users.tasks.save_yesterday_contributions")
    @patch("users.tasks.get_initial_info")
    def test_daily_update_continues_after_user_cache_failure(
        self,
        get_initial_info,
        save_yesterday_contributions,
        refresh_rankings,
    ):
        successful_user = get_user_model().objects.create_user(
            username="cache-success",
            github_email="cache-success@example.com",
            name="캐시 성공 사용자",
            student_id=5,
            major="IT공학",
        )
        get_initial_info.return_value = {
            "data": {
                "user": {
                    "repositories": {
                        "nodes": [{"stargazerCount": 7}],
                    }
                }
            }
        }
        refresh_rankings.side_effect = [RuntimeError("cache failed"), None]

        daily_update.run(period_end="2026-08-25")

        self.assertEqual(save_yesterday_contributions.call_count, 2)
        self.assertEqual(refresh_rankings.call_count, 2)
        refresh_rankings.assert_called_with(
            user_id=successful_user.pk,
            period_end=date(2026, 8, 25),
        )

    @patch("users.tasks.requests.post")
    def test_updates_existing_activity_for_same_day(self, post):
        post.return_value.json.side_effect = [
            {
                "data": {
                    "user": {
                        "contributionsCollection": {
                            "totalCommitContributions": 1,
                            "pullRequestContributions": {"totalCount": 1},
                            "issueContributionsByRepository": [],
                        }
                    }
                }
            },
            {
                "data": {
                    "user": {
                        "contributionsCollection": {
                            "totalCommitContributions": 2,
                            "pullRequestContributions": {"totalCount": 3},
                            "issueContributionsByRepository": [],
                        }
                    }
                }
            },
        ]
        activity_date = date(2026, 8, 25)

        save_yesterday_contributions(
            self.user,
            stars=4,
            activity_date=activity_date,
        )
        save_yesterday_contributions(
            self.user,
            stars=5,
            activity_date=activity_date,
        )

        activity = UserActivity.objects.get(
            user=self.user,
            activity_date=activity_date,
        )
        self.assertEqual(activity.stars, 5)
        self.assertEqual(activity.commits, 2)
        self.assertEqual(activity.prs, 3)

    @patch("users.tasks.refresh_user_ranking_caches")
    @patch("users.tasks.save_previous_contributions")
    @patch("users.tasks.get_initial_info")
    def test_initial_process_refreshes_both_ranking_caches(
        self,
        get_initial_info,
        save_previous_contributions,
        refresh_rankings,
    ):
        get_initial_info.return_value = {
            "data": {
                "user": {
                    "createdAt": "2026-01-01T00:00:00Z",
                    "repositories": {
                        "nodes": [
                            {"stargazerCount": 3},
                            {"stargazerCount": 4},
                        ]
                    },
                }
            }
        }

        initial_process.run(self.user.username)

        period_end = datetime.now(UTC).date() - timedelta(days=1)
        activity = UserActivity.objects.get(
            user=self.user,
            activity_date=period_end,
        )
        self.assertEqual(activity.stars, 7)
        save_previous_contributions.assert_called_once_with(
            self.user,
            "2026-01-01T00:00:00Z",
        )
        refresh_rankings.assert_called_once_with(
            user_id=self.user.pk,
            period_end=period_end,
        )


class UserRankingCacheTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ranking-cache",
            github_email="ranking-cache@example.com",
            name="랭킹 캐시 사용자",
            student_id=4,
            major="IT공학",
        )

    def test_refreshes_one_year_and_six_month_caches_together(self):
        UserActivity.objects.create(
            user=self.user,
            activity_date=date(2025, 12, 1),
            stars=3,
            commits=4,
            prs=2,
            issues=1,
        )
        UserActivity.objects.create(
            user=self.user,
            activity_date=date(2026, 8, 25),
            stars=7,
            commits=3,
            prs=1,
            issues=2,
        )

        refresh_user_ranking_caches(
            user_id=self.user.pk,
            period_end=date(2026, 8, 26),
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.stars, 7)
        self.assertEqual(self.user.commits, 7)
        self.assertEqual(self.user.prs, 3)
        self.assertEqual(self.user.issues, 3)
        self.assertEqual(self.user.score, 20)

        six_month = SixMonthUserRanking.objects.get(user=self.user)
        self.assertEqual(six_month.stars, 7)
        self.assertEqual(six_month.commits, 3)
        self.assertEqual(six_month.pull_requests, 1)
        self.assertEqual(six_month.issues, 2)
        self.assertEqual(six_month.total_score, 13)
        self.assertEqual(six_month.period_start, date(2026, 2, 28))
        self.assertEqual(six_month.period_end, date(2026, 8, 26))

    def test_refreshes_caches_for_user_joined_after_period_end(self):
        period_end = self.user.date_joined.date() - timedelta(days=1)
        UserActivity.objects.create(
            user=self.user,
            activity_date=period_end,
            stars=7,
            commits=3,
            prs=1,
            issues=2,
        )

        refresh_user_ranking_caches(
            user_id=self.user.pk,
            period_end=period_end,
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 13)
        six_month = SixMonthUserRanking.objects.get(user=self.user)
        self.assertEqual(six_month.total_score, 13)
        self.assertEqual(six_month.period_end, period_end)

    def test_admin_period_excludes_user_joined_after_period_end(self):
        period_end = self.user.date_joined.date() - timedelta(days=1)

        results = calculate_user_rankings(period_end, period_end)

        self.assertEqual(results, [])

    def test_six_month_cache_matches_admin_period_calculation(self):
        get_user_model().objects.filter(pk=self.user.pk).update(
            date_joined=datetime(2026, 2, 27, tzinfo=UTC)
        )
        UserActivity.objects.create(
            user=self.user,
            activity_date=date(2026, 2, 27),
            commits=100,
        )
        UserActivity.objects.create(
            user=self.user,
            activity_date=date(2026, 2, 28),
            commits=1,
        )

        refresh_user_ranking_caches(
            user_id=self.user.pk,
            period_end=date(2026, 8, 26),
        )

        six_month = SixMonthUserRanking.objects.get(user=self.user)
        admin_result = calculate_user_rankings(
            six_month.period_start,
            six_month.period_end,
        )[0]

        self.assertEqual(six_month.commits, 1)
        self.assertEqual(six_month.period_start, date(2026, 2, 28))
        self.assertEqual(admin_result.commits, six_month.commits)

    def test_one_year_cache_preserves_365_day_window(self):
        UserActivity.objects.create(
            user=self.user,
            activity_date=date(2025, 8, 26),
            commits=100,
        )
        UserActivity.objects.create(
            user=self.user,
            activity_date=date(2025, 8, 27),
            commits=1,
        )

        refresh_user_ranking_caches(
            user_id=self.user.pk,
            period_end=date(2026, 8, 26),
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.commits, 1)

    def test_rolls_back_both_caches_when_six_month_save_fails(self):
        UserActivity.objects.create(
            user=self.user,
            activity_date=date(2026, 8, 25),
            stars=7,
            commits=3,
            prs=1,
            issues=2,
        )

        with (
            patch.object(
                SixMonthUserRanking.objects,
                "update_or_create",
                side_effect=RuntimeError("cache save failed"),
            ),
            self.assertRaises(RuntimeError),
        ):
            refresh_user_ranking_caches(
                user_id=self.user.pk,
                period_end=date(2026, 8, 26),
            )

        self.user.refresh_from_db()
        self.assertEqual(self.user.score, 0)
        self.assertFalse(
            SixMonthUserRanking.objects.filter(user=self.user).exists()
        )


class UserRankingTargetTests(TestCase):
    period_start = date(2026, 10, 1)
    period_end = date(2026, 10, 27)

    def setUp(self):
        user_model = get_user_model()
        self.active_user = user_model.objects.create_user(
            username="active-user",
            github_email="active-user@example.com",
            name="활동 사용자",
            student_id=11,
            major="IT공학",
        )
        self.starred_user = user_model.objects.create_user(
            username="starred-user",
            github_email="starred-user@example.com",
            name="Star 사용자",
            student_id=12,
            major="IT공학",
        )
        self.inactive_user = user_model.objects.create_user(
            username="inactive-user",
            github_email="inactive-user@example.com",
            name="비활동 사용자",
            student_id=13,
            major="IT공학",
        )
        self.superuser = user_model.objects.create_superuser(
            username="ranking-superuser",
            email="ranking-superuser@example.com",
            password="password",
            github_email="ranking-superuser@example.com",
            name="관리자",
            student_id=14,
            major="IT공학",
        )
        user_model.objects.update(date_joined=datetime(2026, 1, 1, tzinfo=UTC))
        self.create_activity(
            self.active_user,
            date(2026, 9, 30),
            stars=2,
            commits=100,
            prs=100,
            issues=100,
        )
        self.create_activity(
            self.active_user,
            date(2026, 10, 1),
            stars=4,
            commits=1,
            prs=2,
            issues=3,
        )
        self.create_activity(
            self.active_user,
            date(2026, 10, 27),
            stars=None,
            commits=10,
            prs=20,
            issues=30,
        )
        self.create_activity(
            self.active_user,
            date(2026, 10, 28),
            stars=50,
            commits=1000,
            prs=1000,
            issues=1000,
        )
        self.create_activity(
            self.starred_user,
            date(2026, 8, 1),
            stars=9,
            commits=5,
        )
        self.create_activity(
            self.starred_user,
            date(2026, 10, 15),
            stars=None,
            commits=7,
            issues=1,
        )
        self.create_activity(
            self.superuser,
            date(2026, 10, 10),
            stars=1,
            commits=99,
        )

    def create_activity(self, user, activity_date, **metrics):
        UserActivity.objects.create(
            user=user,
            activity_date=activity_date,
            **metrics,
        )

    def ranking_metrics(self, user):
        return (
            int(user.ranking_stars),
            int(user.ranking_commits),
            int(user.ranking_prs),
            int(user.ranking_issues),
        )

    def list_targets(self):
        return {
            user.username: user
            for user in list_user_ranking_targets(
                self.period_start,
                self.period_end,
            )
        }

    def test_sums_only_activities_within_period(self):
        targets = self.list_targets()

        self.assertEqual(
            self.ranking_metrics(targets["active-user"])[1:],
            (11, 22, 33),
        )
        self.assertEqual(
            self.ranking_metrics(targets["starred-user"])[1:],
            (7, 0, 1),
        )

    def test_uses_latest_stars_until_period_end(self):
        targets = self.list_targets()

        self.assertEqual(targets["active-user"].ranking_stars, 4)
        self.assertEqual(targets["starred-user"].ranking_stars, 9)

    def test_user_without_activity_has_zero_metrics(self):
        targets = self.list_targets()

        self.assertEqual(
            self.ranking_metrics(targets["inactive-user"]),
            (0, 0, 0, 0),
        )

    def test_excludes_superuser(self):
        targets = self.list_targets()

        self.assertEqual(
            sorted(targets),
            ["active-user", "inactive-user", "starred-user"],
        )

    def test_single_target_matches_period_list(self):
        for username, listed in self.list_targets().items():
            with self.subTest(username=username):
                target = get_user_ranking_target(
                    user_id=listed.pk,
                    period_start=self.period_start,
                    period_end=self.period_end,
                )

                self.assertEqual(
                    self.ranking_metrics(target),
                    self.ranking_metrics(listed),
                )

    def test_calculates_metrics_without_joining_activities(self):
        # 활동 행을 조인해 GROUP BY 하면 MySQL이 Star 서브쿼리를 활동 행마다
        # 실행해 조회 시간이 활동 누적량에 따라 급격히 늘어난다.
        with self.assertNumQueries(1) as queries:
            list_user_ranking_targets(self.period_start, self.period_end)

        self.assertNotIn(" JOIN ", queries.captured_queries[0]["sql"])


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


class PublicUserProfileApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="profile-user",
            github_email="profile@example.com",
            name="프로필 사용자",
            student_id=20260001,
            major="소프트웨어학부",
            score=999,
            commits=998,
            stars=997,
            prs=996,
            issues=995,
        )

    def test_returns_six_month_ranking_metrics(self):
        SixMonthUserRanking.objects.create(
            user=self.user,
            total_score=50,
            stars=40,
            commits=30,
            pull_requests=20,
            issues=10,
            period_start=date(2026, 2, 27),
            period_end=date(2026, 8, 25),
        )

        with self.assertNumQueries(1):
            response = self.client.get("/api/v1/users/@profile-user")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {
                key: response.json()[key]
                for key in ("score", "stars", "commits", "prs", "issues")
            },
            {
                "score": 50,
                "stars": 40,
                "commits": 30,
                "prs": 20,
                "issues": 10,
            },
        )

    def test_returns_zero_metrics_without_six_month_cache(self):
        with self.assertNumQueries(1):
            response = self.client.get("/api/v1/users/@profile-user")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {
                key: response.json()[key]
                for key in ("score", "stars", "commits", "prs", "issues")
            },
            {
                "score": 0,
                "stars": 0,
                "commits": 0,
                "prs": 0,
                "issues": 0,
            },
        )
