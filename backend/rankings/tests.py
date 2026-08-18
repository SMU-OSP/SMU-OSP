from datetime import date, datetime
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase, override_settings

from projects.models import (
    Project,
    Repository,
    RepositorySnapshot,
)

from .models import ProjectRanking
from .selectors import list_project_ranking_targets, list_project_rankings
from .services import calculate_project_rankings, replace_project_rankings
from .tasks import calculate_daily_project_rankings


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

    def test_calculates_four_metric_deltas(self):
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

        result = calculate_project_rankings(date(2026, 8, 13))[0]

        self.assertEqual(result.project_id, repository.project_id)
        self.assertEqual(result.stars, 5)
        self.assertEqual(result.forks, 2)
        self.assertEqual(result.commits, 15)
        self.assertEqual(result.pull_requests, 4)
        self.assertEqual(result.total_score, Decimal("26.00"))

    def test_clamps_decreased_metric_deltas_to_zero(self):
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

        result = calculate_project_rankings(date(2026, 8, 13))[0]

        self.assertEqual(result.stars, 0)
        self.assertEqual(result.forks, 0)
        self.assertEqual(result.commits, 0)
        self.assertEqual(result.pull_requests, 0)
        self.assertEqual(result.total_score, Decimal("0.00"))

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

        result = calculate_project_rankings(date(2026, 8, 13))[0]

        self.assertEqual(result.stars, 1)
        self.assertEqual(result.commits, 2)
        self.assertEqual(result.pull_requests, 1)
        self.assertEqual(result.period_start, date(2026, 8, 12))

    def test_excludes_projects_outside_ranking_scope(self):
        inactive = self.create_repository_project(
            name="비활성 프로젝트",
            status=Project.Status.INACTIVE,
        )
        self.create_repository_project(name="수집 전 프로젝트")
        self.create_snapshot(
            inactive,
            date(2026, 8, 13),
            stars=1,
            forks=1,
            commits=1,
            pull_requests=1,
        )

        results = calculate_project_rankings(date(2026, 8, 13))

        self.assertEqual(results, [])

    def test_assigns_competition_ranks_and_name_order(self):
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

        results = calculate_project_rankings(date(2026, 8, 13))

        self.assertEqual(
            [(result.rank, result.project_id) for result in results],
            [
                (1, project_ids["가 프로젝트"]),
                (1, project_ids["나 프로젝트"]),
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

        result = calculate_project_rankings(date(2026, 8, 13))[0]

        self.assertEqual(result.total_score, Decimal("3.00"))

    @override_settings(PROJECT_RANKING_STARS_WEIGHT="-0.01")
    def test_rejects_negative_environment_weight(self):
        with self.assertRaises(ImproperlyConfigured):
            calculate_project_rankings(date(2026, 8, 13))

    @override_settings(PROJECT_RANKING_STARS_WEIGHT="not-a-number")
    def test_rejects_non_numeric_environment_weight(self):
        with self.assertRaises(ImproperlyConfigured):
            calculate_project_rankings(date(2026, 8, 13))


class ProjectRankingApiTests(TestCase):
    def test_returns_latest_successful_project_rankings(self):
        project = Project.objects.create(
            name="API 프로젝트",
            description="API 프로젝트 설명",
        )
        replace_project_rankings(
            [
                ProjectRanking(
                    rank=1,
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
            response = self.client.get("/api/v1/rankings/projects")

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
                    rank=rank,
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
        replace_project_rankings(rankings)

        with self.assertNumQueries(1):
            response = self.client.get(
                "/api/v1/rankings/projects",
                {"start": 5, "limit": 5},
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


class ProjectRankingTaskTests(TestCase):
    @patch("rankings.tasks.replace_project_rankings")
    @patch("rankings.tasks.calculate_project_rankings")
    def test_calculates_independently_of_repository_refresh_state(
        self,
        calculate_rankings,
        replace_rankings,
    ):
        calculate_rankings.return_value = [object(), object()]

        result_count = calculate_daily_project_rankings.run(
            period_end="2026-08-13"
        )

        self.assertEqual(result_count, 2)
        calculate_rankings.assert_called_once_with(date(2026, 8, 13))
        replace_rankings.assert_called_once_with(
            calculate_rankings.return_value
        )

    @patch("rankings.tasks.replace_project_rankings")
    @patch("rankings.tasks.calculate_project_rankings")
    @patch("rankings.tasks.datetime")
    def test_default_period_excludes_current_day(
        self,
        task_datetime,
        calculate_rankings,
        replace_rankings,
    ):
        task_datetime.now.return_value = datetime(2026, 8, 14, 3, 10)
        calculate_rankings.return_value = []

        calculate_daily_project_rankings.run()

        calculate_rankings.assert_called_once_with(date(2026, 8, 13))
        replace_rankings.assert_called_once_with([])

    @patch(
        "rankings.tasks.calculate_project_rankings",
        side_effect=RuntimeError("calculation failed"),
    )
    def test_failed_calculation_keeps_last_stored_result(self, _):
        expected = [
            ProjectRanking(
                rank=1,
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
        replace_project_rankings(expected)

        with self.assertRaises(RuntimeError):
            calculate_daily_project_rankings.run(period_end="2026-08-13")

        actual, count = list_project_rankings(start=0, limit=10)
        self.assertEqual(actual[0].project, project)
        self.assertEqual(actual[0].total_score, Decimal("1.00"))
        self.assertEqual(count, 1)

    def test_failed_replacement_keeps_last_stored_result(self):
        project = Project.objects.create(
            name="교체 실패 프로젝트",
            description="교체 실패 프로젝트 설명",
        )
        expected = ProjectRanking(
            rank=1,
            project_id=project.pk,
            total_score=Decimal("1.00"),
            stars=1,
            forks=0,
            commits=0,
            pull_requests=0,
            period_start=date(2025, 8, 13),
            period_end=date(2026, 8, 13),
        )
        replace_project_rankings([expected])

        with (
            patch(
                "rankings.services.ProjectRanking.objects.bulk_create",
                side_effect=RuntimeError("replacement failed"),
            ),
            self.assertRaises(RuntimeError),
        ):
            replace_project_rankings([])

        ranking = ProjectRanking.objects.get()
        self.assertEqual(ranking.project, project)
        self.assertEqual(ranking.total_score, Decimal("1.00"))

    def test_ranking_beat_schedule_runs_once_at_six(self):
        ranking = settings.CELERY_BEAT_SCHEDULE["project-ranking"]
        self.assertEqual(
            ranking["task"],
            "rankings.tasks.calculate_daily_project_rankings",
        )
        self.assertEqual(ranking["schedule"].minute, {0})
        self.assertEqual(ranking["schedule"].hour, {6})
