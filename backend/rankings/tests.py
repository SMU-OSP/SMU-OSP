from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import call, patch
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings
from django.urls import reverse

from common.dates import ranking_period_boundary
from projects.models import (
    Project,
    Repository,
    RepositorySnapshot,
)
from users.models import SixMonthUserRanking, User, UserActivity
from users.services import calculate_user_rankings

from .models import (
    ProjectRanking,
    SixMonthProjectRanking,
)
from .selectors import list_project_ranking_targets, list_project_rankings
from .services import (
    calculate_project_rankings,
    replace_daily_project_rankings,
)
from .tasks import (
    calculate_daily_project_rankings,
    refresh_users_and_calculate_rankings,
)


class ProjectRankingCalculationTests(TestCase):
    def create_repository_project(
        self,
        *,
        name: str,
        status: str = Project.Status.ACTIVE,
    ) -> Repository:
        project = Project.objects.create(
            name=name,
            description=f"{name} 설명",
            status=status,
        )
        return Repository.objects.create(
            project=project,
            github_id=project.pk,
            name=f"repository-{project.pk}",
            full_name=f"example/repository-{project.pk}",
            html_url=f"https://github.com/example/repository-{project.pk}",
        )

    def create_snapshot(
        self,
        repository: Repository,
        snapshot_date: date,
        *,
        stars: int,
        forks: int,
        commits: int,
        pull_requests: int,
    ) -> None:
        RepositorySnapshot.objects.create(
            repository=repository,
            date=snapshot_date,
            stars=stars,
            forks=forks,
            commits=commits,
            pull_requests=pull_requests,
            has_code_changed=False,
        )

    def test_calculates_cumulative_stars_and_metric_deltas(self):
        repository = self.create_repository_project(name="계산 프로젝트")
        snapshots = (
            (date(2025, 8, 13), 10, 2, 20, 3),
            (date(2026, 8, 10), 12, 3, 25, 5),
            (date(2026, 8, 11), 13, 3, 26, 5),
            (date(2026, 8, 12), 14, 4, 30, 6),
            (date(2026, 8, 13), 15, 4, 35, 7),
        )
        for snapshot in snapshots:
            self.create_snapshot(
                repository,
                snapshot[0],
                stars=snapshot[1],
                forks=snapshot[2],
                commits=snapshot[3],
                pull_requests=snapshot[4],
            )

        result = calculate_project_rankings(
            date(2025, 8, 13),
            date(2026, 8, 13),
        )[0]

        self.assertEqual(result.project_id, repository.project_id)
        self.assertEqual(result.stars, 15)
        self.assertEqual(result.forks, 2)
        self.assertEqual(result.commits, 15)
        self.assertEqual(result.pull_requests, 4)
        self.assertEqual(result.total_score, Decimal("36.00"))

    def test_calculates_project_ranking_for_selected_period(self):
        repository = self.create_repository_project(name="기간 선택 프로젝트")
        for snapshot_date, commits in (
            (date(2026, 7, 31), 5),
            (date(2026, 8, 10), 7),
            (date(2026, 8, 20), 12),
        ):
            self.create_snapshot(
                repository,
                snapshot_date,
                stars=3,
                forks=0,
                commits=commits,
                pull_requests=0,
            )

        result = calculate_project_rankings(
            date(2026, 8, 10),
            date(2026, 8, 20),
        )[0]

        self.assertEqual(result.commits, 5)
        self.assertEqual(result.period_start, date(2026, 8, 10))
        self.assertEqual(result.period_end, date(2026, 8, 20))
        with self.assertNumQueries(0):
            self.assertEqual(result.project.name, "기간 선택 프로젝트")

    def test_clamps_decreased_deltas_but_keeps_cumulative_stars(self):
        repository = self.create_repository_project(name="감소 지표 프로젝트")
        self.create_snapshot(
            repository,
            date(2025, 8, 13),
            stars=10,
            forks=4,
            commits=20,
            pull_requests=5,
        )
        self.create_snapshot(
            repository,
            date(2026, 8, 13),
            stars=9,
            forks=3,
            commits=15,
            pull_requests=4,
        )

        result = calculate_project_rankings(
            date(2025, 8, 13),
            date(2026, 8, 13),
        )[0]

        self.assertEqual(result.stars, 9)
        self.assertEqual(result.forks, 0)
        self.assertEqual(result.commits, 0)
        self.assertEqual(result.pull_requests, 0)
        self.assertEqual(result.total_score, Decimal("9.00"))

    def test_loads_only_boundary_and_latest_snapshots(self):
        repository = self.create_repository_project(name="기간 제한 프로젝트")
        for snapshot_date in (
            date(2024, 8, 13),
            date(2025, 8, 12),
            date(2026, 8, 12),
            date(2026, 8, 13),
        ):
            self.create_snapshot(
                repository,
                snapshot_date,
                stars=0,
                forks=0,
                commits=0,
                pull_requests=0,
            )

        project = list_project_ranking_targets(
            date(2025, 8, 13),
            date(2026, 8, 13),
        )[0]

        self.assertEqual(
            [snapshot.date for snapshot in project.repository.ranking_snapshots],
            [date(2025, 8, 12), date(2026, 8, 13)],
        )

    def test_uses_first_available_snapshot_for_short_history(self):
        repository = self.create_repository_project(name="신규 프로젝트")
        self.create_snapshot(
            repository,
            date(2026, 8, 12),
            stars=10,
            forks=2,
            commits=5,
            pull_requests=1,
        )
        self.create_snapshot(
            repository,
            date(2026, 8, 13),
            stars=11,
            forks=2,
            commits=7,
            pull_requests=2,
        )

        result = calculate_project_rankings(
            date(2025, 8, 13),
            date(2026, 8, 13),
        )[0]

        self.assertEqual(result.stars, 11)
        self.assertEqual(result.commits, 2)
        self.assertEqual(result.pull_requests, 1)
        self.assertEqual(result.period_start, date(2026, 8, 12))

    def test_includes_projects_with_snapshots_regardless_of_status(self):
        repositories = [
            self.create_repository_project(
                name=f"{status} 프로젝트",
                status=status,
            )
            for status in (
                Project.Status.INACTIVE,
                Project.Status.FINISHED,
                Project.Status.DELETED,
            )
        ]
        self.create_repository_project(name="수집 전 프로젝트")
        for repository in repositories:
            self.create_snapshot(
                repository,
                date(2026, 8, 13),
                stars=1,
                forks=1,
                commits=1,
                pull_requests=1,
            )

        results = calculate_project_rankings(
            date(2025, 8, 13),
            date(2026, 8, 13),
        )

        self.assertEqual(
            {result.project_id for result in results},
            {repository.project_id for repository in repositories},
        )

    def test_assigns_sequential_ranks_and_name_order(self):
        project_ids = {}
        for name, stars in (
            ("나 프로젝트", 5),
            ("다 프로젝트", 1),
            ("가 프로젝트", 5),
        ):
            repository = self.create_repository_project(name=name)
            project_ids[name] = repository.project_id
            self.create_snapshot(
                repository,
                date(2025, 8, 13),
                stars=0,
                forks=0,
                commits=0,
                pull_requests=0,
            )
            self.create_snapshot(
                repository,
                date(2026, 8, 13),
                stars=stars,
                forks=0,
                commits=0,
                pull_requests=0,
            )

        results = calculate_project_rankings(
            date(2025, 8, 13),
            date(2026, 8, 13),
        )

        self.assertEqual(
            [(result.rank, result.project_id) for result in results],
            [
                (1, project_ids["가 프로젝트"]),
                (2, project_ids["나 프로젝트"]),
                (3, project_ids["다 프로젝트"]),
            ],
        )

    @override_settings(
        PROJECT_RANKING_STARS_WEIGHT="0.00",
        PROJECT_RANKING_COMMITS_WEIGHT="1.50",
    )
    def test_uses_environment_weights(self):
        repository = self.create_repository_project(name="가중치 프로젝트")
        self.create_snapshot(
            repository,
            date(2025, 8, 13),
            stars=0,
            forks=0,
            commits=0,
            pull_requests=0,
        )
        self.create_snapshot(
            repository,
            date(2026, 8, 13),
            stars=100,
            forks=0,
            commits=2,
            pull_requests=0,
        )

        result = calculate_project_rankings(
            date(2025, 8, 13),
            date(2026, 8, 13),
        )[0]

        self.assertEqual(result.total_score, Decimal("3.00"))

    @override_settings(PROJECT_RANKING_STARS_WEIGHT="-0.01")
    def test_rejects_negative_environment_weight(self):
        with self.assertRaises(ImproperlyConfigured):
            calculate_project_rankings(
                date(2025, 8, 13),
                date(2026, 8, 13),
            )

    @override_settings(PROJECT_RANKING_STARS_WEIGHT="not-a-number")
    def test_rejects_non_numeric_environment_weight(self):
        with self.assertRaises(ImproperlyConfigured):
            calculate_project_rankings(
                date(2025, 8, 13),
                date(2026, 8, 13),
            )


class ProjectRankingApiTests(TestCase):
    def test_returns_latest_successful_project_rankings(self):
        project = Project.objects.create(
            name="API 프로젝트",
            description="API 프로젝트 설명",
        )
        ProjectRanking.objects.bulk_create(
            [
                ProjectRanking(
                    project_id=project.pk,
                    total_score=Decimal("12.50"),
                    stars=2,
                    forks=1,
                    commits=3,
                    pull_requests=1,
                    period_start=date(2025, 8, 13),
                    period_end=date(2026, 8, 13),
                )
            ]
        )

        with self.assertNumQueries(1):
            response = self.client.get(
                "/api/v1/rankings/projects",
                {"period": "1y"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(body["data"][0]["projectId"], project.pk)
        self.assertEqual(body["data"][0]["totalScore"], "12.50")
        self.assertNotIn("actualPeriodStart", body["data"][0])
        self.assertEqual(body["detail"]["pagination"]["count"], 1)

    def test_returns_empty_success_before_first_calculation(self):
        with self.assertNumQueries(1):
            response = self.client.get("/api/v1/rankings/projects")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [])
        self.assertEqual(
            response.json()["detail"]["pagination"],
            {
                "start": 0,
                "limit": 100,
                "count": 0,
                "currentPage": 1,
                "totalPages": 1,
                "hasPrevious": False,
                "hasNext": False,
            },
        )

    def test_paginates_latest_project_rankings(self):
        rankings = []
        for rank in range(1, 13):
            project = Project.objects.create(
                name=f"프로젝트 {rank:02d}",
                description="페이지네이션 테스트",
            )
            rankings.append(
                ProjectRanking(
                    project_id=project.pk,
                    total_score=Decimal("1.00"),
                    stars=1,
                    forks=0,
                    commits=0,
                    pull_requests=0,
                    period_start=date(2025, 8, 13),
                    period_end=date(2026, 8, 13),
                )
            )
        ProjectRanking.objects.bulk_create(rankings)

        with self.assertNumQueries(1):
            response = self.client.get(
                "/api/v1/rankings/projects",
                {"start": 5, "limit": 5, "period": "1y"},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            [result["rank"] for result in body["data"]],
            [6, 7, 8, 9, 10],
        )
        self.assertEqual(
            body["detail"]["pagination"],
            {
                "start": 5,
                "limit": 5,
                "count": 12,
                "currentPage": 2,
                "totalPages": 3,
                "hasPrevious": True,
                "hasNext": True,
            },
        )

    def test_rejects_invalid_pagination(self):
        response = self.client.get(
            "/api/v1/rankings/projects",
            {"start": -1, "limit": 101},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["status"], "INVALID_PAGINATION_PARAMETER"
        )

    def test_returns_saved_six_month_project_rankings_by_default(self):
        first_project = Project.objects.create(
            name="상위 6개월 프로젝트",
            description="상위 6개월 프로젝트 설명",
        )
        second_project = Project.objects.create(
            name="6개월 프로젝트",
            description="6개월 프로젝트 설명",
        )
        SixMonthProjectRanking.objects.bulk_create(
            [
                SixMonthProjectRanking(
                    project=first_project,
                    total_score=Decimal("9.00"),
                    period_start=date(2026, 2, 20),
                    period_end=date(2026, 8, 20),
                ),
                SixMonthProjectRanking(
                    project=second_project,
                    total_score=Decimal("8.00"),
                    stars=3,
                    forks=0,
                    commits=5,
                    pull_requests=0,
                    period_start=date(2026, 2, 20),
                    period_end=date(2026, 8, 20),
                ),
            ]
        )

        with self.assertNumQueries(1):
            response = self.client.get(
                "/api/v1/rankings/projects",
                {"start": 1, "limit": 1},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"][0]["projectId"], second_project.pk)
        self.assertEqual(body["data"][0]["rank"], 2)
        self.assertEqual(body["data"][0]["commits"], 5)
        self.assertEqual(body["detail"]["pagination"]["count"], 2)
        self.assertEqual(ProjectRanking.objects.count(), 0)

    def test_rejects_invalid_ranking_period(self):
        response = self.client.get(
            "/api/v1/rankings/projects",
            {"period": "3m"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "INVALID_RANKING_PERIOD")


class UserRankingApiTests(TestCase):
    def test_returns_saved_one_year_user_rankings(self):
        top_user = User.objects.create_user(
            username="saved-top-user",
            password="password",
            github_email="saved-top@example.com",
            name="저장 랭킹 1위",
            student_id=20260001,
            major="컴퓨터과학",
            score=20,
            stars=5,
            commits=6,
            prs=4,
            issues=5,
        )
        User.objects.create_user(
            username="saved-second-user",
            password="password",
            github_email="saved-second@example.com",
            name="저장 랭킹 2위",
            student_id=20260002,
            major="컴퓨터과학",
            score=10,
        )
        UserActivity.objects.create(
            user=top_user,
            activity_date=date(2026, 8, 20),
            stars=100,
            commits=100,
            prs=100,
            issues=100,
        )

        with self.assertNumQueries(1):
            response = self.client.get(
                "/api/v1/rankings/users",
                {"period": "1y", "limit": 1},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"][0]["username"], top_user.username)
        self.assertEqual(body["data"][0]["totalScore"], 20)
        self.assertEqual(body["data"][0]["stars"], 5)
        self.assertEqual(body["data"][0]["pullRequests"], 4)
        self.assertEqual(body["detail"]["pagination"]["count"], 2)

    def test_derives_one_year_rank_after_pagination(self):
        for index, score in enumerate((20, 10)):
            User.objects.create_user(
                username=f"one-year-user-{index}",
                password="password",
                github_email=f"one-year-{index}@example.com",
                name=f"1년 사용자 {index}",
                student_id=20260020 + index,
                major="컴퓨터과학",
                score=score,
            )

        with self.assertNumQueries(1):
            response = self.client.get(
                "/api/v1/rankings/users",
                {"period": "1y", "start": 1, "limit": 1},
            )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"][0]["rank"], 2)
        self.assertEqual(body["data"][0]["username"], "one-year-user-1")
        self.assertEqual(body["detail"]["pagination"]["count"], 2)

    def test_returns_saved_six_month_user_rankings_by_default(self):
        user = User.objects.create_user(
            username="six-month-user",
            password="password",
            github_email="six-month@example.com",
            name="6개월 사용자",
            student_id=20260001,
            major="컴퓨터과학",
            score=999,
            stars=999,
            commits=999,
            prs=999,
            issues=999,
        )
        SixMonthUserRanking.objects.create(
            user=user,
            total_score=10,
            stars=4,
            commits=3,
            pull_requests=2,
            issues=1,
            period_start=date(2026, 2, 20),
            period_end=date(2026, 8, 20),
        )
        UserActivity.objects.create(
            user=user,
            activity_date=date(2026, 8, 20),
            stars=100,
            commits=100,
            prs=100,
            issues=100,
        )

        with self.assertNumQueries(1):
            response = self.client.get("/api/v1/rankings/users")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"][0]["rank"], 1)
        self.assertEqual(body["data"][0]["username"], user.username)
        self.assertEqual(body["data"][0]["totalScore"], 10)
        self.assertEqual(body["data"][0]["pullRequests"], 2)
        self.assertEqual(body["detail"]["pagination"]["count"], 1)

    def test_derives_six_month_rank_after_pagination(self):
        users = [
            User.objects.create_user(
                username=f"six-month-user-{index}",
                password="password",
                github_email=f"six-month-{index}@example.com",
                name=f"6개월 사용자 {index}",
                student_id=20260010 + index,
                major="컴퓨터과학",
            )
            for index in range(2)
        ]
        for user, score in zip(users, (20, 10), strict=True):
            SixMonthUserRanking.objects.create(
                user=user,
                total_score=score,
                period_start=date(2026, 2, 20),
                period_end=date(2026, 8, 20),
            )

        response = self.client.get(
            "/api/v1/rankings/users",
            {"start": 1, "limit": 1},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data"][0]["rank"], 2)
        self.assertEqual(body["data"][0]["username"], users[1].username)
        self.assertEqual(body["detail"]["pagination"]["count"], 2)

    def test_uses_fixed_180_day_period_boundary(self):
        self.assertEqual(
            ranking_period_boundary(date(2026, 8, 31), 180),
            date(2026, 3, 4),
        )


class ProjectRankingTaskTests(TestCase):
    @patch("rankings.tasks.replace_daily_project_rankings")
    @patch("rankings.tasks.calculate_project_rankings")
    def test_calculates_independently_of_repository_refresh_state(
        self,
        calculate_projects,
        replace_rankings,
    ):
        one_year_projects = [object(), object()]
        six_month_projects = [object()]
        calculate_projects.side_effect = [
            one_year_projects,
            six_month_projects,
        ]

        result_count = calculate_daily_project_rankings.run(
            period_end="2026-08-13"
        )

        self.assertEqual(result_count, 3)
        self.assertEqual(
            calculate_projects.call_args_list,
            [
                call(date(2025, 8, 13), date(2026, 8, 13)),
                call(date(2026, 2, 14), date(2026, 8, 13)),
            ],
        )
        replace_rankings.assert_called_once_with(
            one_year_projects=one_year_projects,
            six_month_projects=six_month_projects,
        )

    @patch("rankings.tasks.replace_daily_project_rankings")
    @patch("rankings.tasks.calculate_project_rankings")
    @patch("rankings.tasks.datetime")
    def test_default_period_excludes_current_day(
        self,
        task_datetime,
        calculate_projects,
        replace_rankings,
    ):
        task_datetime.now.return_value = datetime(2026, 8, 14, 3, 10)
        calculate_projects.return_value = []

        calculate_daily_project_rankings.run()

        task_datetime.now.assert_called_once_with(UTC)
        self.assertEqual(
            calculate_projects.call_args_list,
            [
                call(date(2025, 8, 13), date(2026, 8, 13)),
                call(date(2026, 2, 14), date(2026, 8, 13)),
            ],
        )
        replace_rankings.assert_called_once()

    @patch(
        "rankings.tasks.calculate_project_rankings",
        side_effect=RuntimeError("calculation failed"),
    )
    def test_failed_calculation_keeps_last_stored_result(self, _):
        expected = [
            ProjectRanking(
                project_id=1,
                total_score=Decimal("1.00"),
                stars=1,
                forks=0,
                commits=0,
                pull_requests=0,
                period_start=date(2025, 8, 13),
                period_end=date(2026, 8, 13),
            )
        ]
        project = Project.objects.create(
            id=1,
            name="마지막 정상 프로젝트",
            description="마지막 정상 프로젝트 설명",
        )
        ProjectRanking.objects.bulk_create(expected)
        SixMonthProjectRanking.objects.create(
            project=project,
            total_score=Decimal("2.00"),
            period_start=date(2026, 2, 13),
            period_end=date(2026, 8, 13),
        )
        with self.assertRaises(RuntimeError):
            calculate_daily_project_rankings.run(period_end="2026-08-13")

        actual, count = list_project_rankings(start=0, limit=10)
        self.assertEqual(actual[0].project, project)
        self.assertEqual(actual[0].total_score, Decimal("1.00"))
        self.assertEqual(count, 1)
        self.assertEqual(
            SixMonthProjectRanking.objects.get().total_score,
            2,
        )

    def test_failed_project_replacement_keeps_both_stored_results(self):
        project = Project.objects.create(
            name="교체 실패 프로젝트",
            description="교체 실패 프로젝트 설명",
        )
        expected = ProjectRanking(
            project_id=project.pk,
            total_score=Decimal("1.00"),
            stars=1,
            forks=0,
            commits=0,
            pull_requests=0,
            period_start=date(2025, 8, 13),
            period_end=date(2026, 8, 13),
        )
        ProjectRanking.objects.bulk_create([expected])
        SixMonthProjectRanking.objects.create(
            project=project,
            total_score=Decimal("2.00"),
            period_start=date(2026, 2, 13),
            period_end=date(2026, 8, 13),
        )
        with (
            patch(
                "rankings.services.SixMonthProjectRanking.objects.bulk_create",
                side_effect=RuntimeError("replacement failed"),
            ),
            self.assertRaises(RuntimeError),
        ):
            replace_daily_project_rankings(
                one_year_projects=[],
                six_month_projects=[],
            )

        ranking = ProjectRanking.objects.get()
        self.assertEqual(ranking.project, project)
        self.assertEqual(ranking.total_score, Decimal("1.00"))
        self.assertEqual(
            SixMonthProjectRanking.objects.get().total_score,
            2,
        )

    def test_replaces_one_year_and_six_month_project_results_together(self):
        project = Project.objects.create(
            name="기간별 저장 프로젝트",
            description="기간별 저장 프로젝트 설명",
        )
        one_year_project = ProjectRanking(
            project=project,
            total_score=Decimal("10.00"),
            period_start=date(2025, 8, 20),
            period_end=date(2026, 8, 20),
        )
        six_month_project = ProjectRanking(
            project=project,
            total_score=Decimal("5.00"),
            period_start=date(2026, 2, 20),
            period_end=date(2026, 8, 20),
        )
        replace_daily_project_rankings(
            one_year_projects=[one_year_project],
            six_month_projects=[six_month_project],
        )

        self.assertEqual(ProjectRanking.objects.get().total_score, 10)
        self.assertEqual(
            SixMonthProjectRanking.objects.get().total_score,
            5,
        )

    @patch("rankings.tasks.datetime")
    @patch("rankings.tasks.chain")
    @patch("rankings.tasks.calculate_daily_project_rankings.si")
    @patch("rankings.tasks.daily_update.si")
    def test_refreshes_users_before_calculating_rankings(
        self,
        user_update_signature,
        ranking_signature,
        task_chain,
        task_datetime,
    ):
        task_datetime.now.return_value = datetime(2026, 8, 26, 3, 10)
        user_update_signature.return_value = "user-update"
        ranking_signature.return_value = "ranking-update"

        refresh_users_and_calculate_rankings.run()

        task_datetime.now.assert_called_once_with(UTC)
        user_update_signature.assert_called_once_with(
            period_end="2026-08-25"
        )
        ranking_signature.assert_called_once_with(
            period_end="2026-08-25"
        )
        task_chain.assert_called_once_with(
            "user-update",
            "ranking-update",
        )
        task_chain.return_value.apply_async.assert_called_once_with()

    def test_ranking_beat_schedule_runs_after_user_refresh(self):
        ranking = settings.CELERY_BEAT_SCHEDULE["project-ranking"]
        self.assertEqual(
            ranking["task"],
            "rankings.tasks.refresh_users_and_calculate_rankings",
        )
        self.assertEqual(ranking["schedule"].minute, {0})
        self.assertEqual(ranking["schedule"].hour, {6})

        user_update = settings.CELERY_BEAT_SCHEDULE["daily-update"]
        self.assertEqual(user_update["schedule"].minute, {0})
        self.assertEqual(user_update["schedule"].hour, {0, 12, 18})


class RankingAdminReportTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="ranking-admin",
            email="admin@example.com",
            password="password",
            github_email="admin@example.com",
            name="관리자",
            student_id=1,
            major="컴퓨터과학",
        )
        self.ranked_user = User.objects.create_user(
            username="@ranked-user",
            password="password",
            github_email="ranked@example.com",
            name="=랭킹 사용자",
            student_id=20260001,
            major="컴퓨터과학",
        )
        User.objects.filter(pk=self.ranked_user.pk).update(
            date_joined=datetime(2026, 1, 1, tzinfo=UTC)
        )
        self.ranked_user.refresh_from_db()
        UserActivity.objects.create(
            user=self.ranked_user,
            activity_date=date(2026, 8, 10),
            stars=3,
            commits=2,
            prs=1,
            issues=0,
        )
        UserActivity.objects.create(
            user=self.ranked_user,
            activity_date=date(2026, 8, 20),
            stars=5,
            commits=4,
            prs=0,
            issues=1,
        )
        self.url = reverse("admin:rankings_projectranking_changelist")
        self.export_url = reverse("admin:rankings_projectranking_export")

    def export_ranking(self, query: dict[str, str], format_name: str = "csv"):
        export_page = self.client.get(self.export_url, query)
        form = export_page.context["form"]
        format_value = next(
            value
            for value, label in form.fields["format"].choices
            if str(label) == format_name
        )
        data = {
            "format": format_value,
            "resource": "0",
        }
        data.update(
            {
                field_name: True
                for field_name, field in form.fields.items()
                if getattr(field, "is_selectable_field", False)
            }
        )
        response = self.client.post(
            f"{self.export_url}?{urlencode(query)}",
            data,
        )
        return export_page, response

    def test_calculates_user_ranking_for_selected_period(self):
        result = calculate_user_rankings(
            date(2026, 8, 10),
            date(2026, 8, 20),
        )[0]

        self.assertEqual(result.user, self.ranked_user)
        self.assertEqual(result.rank, 1)
        self.assertEqual(result.stars, 5)
        self.assertEqual(result.commits, 6)
        self.assertEqual(result.pull_requests, 1)
        self.assertEqual(result.issues, 1)
        self.assertEqual(result.total_score, 13)

    def test_admin_displays_and_exports_same_user_ranking(self):
        self.client.force_login(self.admin_user)
        query = {
            "ranking_type": "users",
            "period_start": "2026-08-10",
            "period_end": "2026-08-20",
        }

        response = self.client.get(self.url, query)
        export_page, csv_response = self.export_ranking(query)

        self.assertContains(response, "@ranked-user")
        self.assertContains(response, "13")
        available_formats = {
            str(label)
            for _, label in export_page.context["form"].fields[
                "format"
            ].choices
        }
        self.assertTrue(
            {"csv", "tsv", "json", "yaml", "html"}.issubset(
                available_formats
            )
        )
        self.assertNotIn("xlsx", available_formats)
        self.assertEqual(csv_response.status_code, 200)
        self.assertTrue(csv_response.content.startswith(b"\xef\xbb\xbf"))
        decoded_csv = csv_response.content.decode("utf-8-sig")
        self.assertIn("'@ranked-user", decoded_csv)
        self.assertEqual(ProjectRanking.objects.count(), 0)

    def test_admin_rejects_reversed_period(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(
            self.url,
            {
                "ranking_type": "users",
                "period_start": "2026-08-20",
                "period_end": "2026-08-10",
            },
        )

        self.assertContains(
            response,
            "종료일은 시작일과 같거나 이후여야 합니다.",
        )

    def test_admin_exports_every_supported_format(self):
        self.client.force_login(self.admin_user)
        query = {
            "ranking_type": "users",
            "period_start": "2026-08-10",
            "period_end": "2026-08-20",
        }

        responses = {}
        for format_name in ("csv", "tsv", "json", "yaml", "html"):
            with self.subTest(format_name=format_name):
                _, response = self.export_ranking(query, format_name)
                responses[format_name] = response

                self.assertEqual(response.status_code, 200)
                self.assertIn(
                    f".{format_name}",
                    response["Content-Disposition"],
                )

        json_content = responses["json"].content.decode("utf-8-sig")
        self.assertIn('"@ranked-user"', json_content)
        self.assertNotIn('"\'@ranked-user"', json_content)

    def test_admin_displays_project_ranking_without_saving_it(self):
        self.client.force_login(self.admin_user)
        project = Project.objects.create(
            name="관리자 조회 프로젝트",
            description="관리자 조회 프로젝트 설명",
        )
        repository = Repository.objects.create(
            project=project,
            github_id=100,
            name="ranking-report",
            full_name="example/ranking-report",
            html_url="https://github.com/example/ranking-report",
        )
        RepositorySnapshot.objects.create(
            repository=repository,
            date=date(2026, 8, 9),
            stars=2,
            forks=0,
            commits=1,
            pull_requests=0,
            has_code_changed=False,
        )
        RepositorySnapshot.objects.create(
            repository=repository,
            date=date(2026, 8, 10),
            stars=2,
            forks=0,
            commits=3,
            pull_requests=0,
            has_code_changed=False,
        )
        RepositorySnapshot.objects.create(
            repository=repository,
            date=date(2026, 8, 20),
            stars=3,
            forks=1,
            commits=8,
            pull_requests=2,
            has_code_changed=False,
        )

        response = self.client.get(
            self.url,
            {
                "ranking_type": "projects",
                "period_start": "2026-08-10",
                "period_end": "2026-08-20",
            },
        )
        _, csv_response = self.export_ranking(
            {
                "ranking_type": "projects",
                "period_start": "2026-08-10",
                "period_end": "2026-08-20",
            }
        )

        self.assertContains(response, "관리자 조회 프로젝트")
        self.assertContains(response, "11.00")
        decoded_csv = csv_response.content.decode("utf-8-sig")
        self.assertIn("순위,프로젝트,총점,Star,Fork,Commit,PR", decoded_csv)
        self.assertIn("관리자 조회 프로젝트", decoded_csv)
        self.assertIn("11.00", decoded_csv)
        self.assertEqual(ProjectRanking.objects.count(), 0)

    def test_admin_requires_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("admin:login"), response.url)
