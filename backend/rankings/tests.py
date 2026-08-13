from datetime import date
from decimal import Decimal
from unittest.mock import patch

from celery.exceptions import Retry
from django.core.exceptions import ValidationError
from django.test import TestCase

from projects.models import (
    Project,
    Repository,
    RepositorySnapshot,
    RepositoryStatus,
)

from .models import (
    ProjectRankingResult,
    ProjectRankingRun,
    ProjectRankingWeight,
)
from .selectors import (
    has_pending_project_ranking_refreshes,
    list_project_ranking_targets,
)
from .services import calculate_project_rankings
from .tasks import (
    RANKING_MAX_RETRIES,
    RANKING_RETRY_DELAY_SECONDS,
    calculate_daily_project_rankings,
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

        run = calculate_project_rankings(date(2026, 8, 13))

        result = run.results.get(project=repository.project)
        self.assertEqual(run.period_start, date(2025, 8, 13))
        self.assertEqual(result.actual_period_start, date(2025, 8, 13))
        self.assertEqual(result.stars, 5)
        self.assertEqual(result.forks, 2)
        self.assertEqual(result.commits, 15)
        self.assertEqual(result.pull_requests, 4)
        self.assertEqual(result.total_score, Decimal("26.00"))

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

        result = calculate_project_rankings(date(2026, 8, 13)).results.get()

        self.assertEqual(result.actual_period_start, date(2026, 8, 12))
        self.assertEqual(result.stars, 1)
        self.assertEqual(result.commits, 2)
        self.assertEqual(result.pull_requests, 1)

    def test_excludes_projects_outside_ranking_scope(self):
        inactive = self.create_repository_project(
            name="비활성 프로젝트",
            status=Project.Status.INACTIVE,
        )
        active_without_snapshot = self.create_repository_project(
            name="수집 전 프로젝트"
        )
        self.create_snapshot(
            inactive,
            date(2026, 8, 13),
            stars=1,
            forks=1,
            commits=1,
            pull_requests=1,
        )

        run = calculate_project_rankings(date(2026, 8, 13))

        self.assertFalse(run.results.exists())
        self.assertFalse(
            run.results.filter(project=active_without_snapshot.project).exists()
        )

    def test_assigns_competition_ranks_and_name_order(self):
        for name, stars in (
            ("가 프로젝트", 5),
            ("나 프로젝트", 5),
            ("다 프로젝트", 1),
        ):
            repository = self.create_repository_project(name=name)
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

        results = list(
            calculate_project_rankings(date(2026, 8, 13))
            .results.select_related("project")
            .order_by("rank", "project__name")
        )

        self.assertEqual(
            [(result.rank, result.project.name) for result in results],
            [(1, "가 프로젝트"), (1, "나 프로젝트"), (3, "다 프로젝트")],
        )

    def test_uses_current_weights_and_preserves_them_in_run(self):
        repository = self.create_repository_project(name="가중치 프로젝트")
        ProjectRankingWeight.objects.create(
            stars=Decimal("0.00"),
            commits=Decimal("1.50"),
        )
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

        run = calculate_project_rankings(date(2026, 8, 13))

        self.assertEqual(run.stars_weight, Decimal("0.00"))
        self.assertEqual(run.commits_weight, Decimal("1.50"))
        self.assertEqual(run.results.get().total_score, Decimal("3.00"))

    def test_failed_calculation_keeps_last_successful_run(self):
        repository = self.create_repository_project(name="정상 결과 프로젝트")
        self.create_snapshot(
            repository,
            date(2026, 8, 13),
            stars=1,
            forks=0,
            commits=0,
            pull_requests=0,
        )
        successful_run = calculate_project_rankings(date(2026, 8, 13))

        with (
            patch.object(
                ProjectRankingResult.objects,
                "bulk_create",
                side_effect=RuntimeError("save failed"),
            ),
            self.assertRaises(RuntimeError),
        ):
            calculate_project_rankings(date(2026, 8, 14))

        self.assertEqual(ProjectRankingRun.objects.count(), 1)
        self.assertEqual(ProjectRankingRun.objects.get(), successful_run)

    def test_weight_rejects_negative_value(self):
        weights = ProjectRankingWeight(stars=Decimal("-0.01"))

        with self.assertRaises(ValidationError):
            weights.full_clean()


class ProjectRankingApiTests(TestCase):
    def test_returns_latest_successful_project_rankings(self):
        project = Project.objects.create(
            name="API 프로젝트",
            description="API 프로젝트 설명",
        )
        run = ProjectRankingRun.objects.create(
            period_start=date(2025, 8, 13),
            period_end=date(2026, 8, 13),
            stars_weight=Decimal("1.00"),
            forks_weight=Decimal("1.00"),
            commits_weight=Decimal("1.00"),
            pull_requests_weight=Decimal("1.00"),
        )
        ProjectRankingResult.objects.create(
            run=run,
            project=project,
            rank=1,
            total_score=Decimal("12.50"),
            stars=2,
            forks=1,
            commits=3,
            pull_requests=1,
            actual_period_start=date(2025, 8, 13),
        )

        response = self.client.get("/api/v1/rankings/projects")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(body["data"][0]["projectId"], project.pk)
        self.assertEqual(body["data"][0]["totalScore"], "12.50")
        self.assertNotIn("actualPeriodStart", body["data"][0])
        self.assertIsNone(body["detail"])

    def test_returns_empty_success_before_first_calculation(self):
        response = self.client.get("/api/v1/rankings/projects")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [])
        self.assertIsNone(response.json()["detail"])


class ProjectRankingTaskTests(TestCase):
    def test_only_active_project_pending_refresh_blocks_ranking(self):
        for status in (Project.Status.ACTIVE, Project.Status.INACTIVE):
            project = Project.objects.create(
                name=f"{status} 프로젝트",
                description="수집 상태 확인 프로젝트",
                status=status,
            )
            repository = Repository.objects.create(
                project=project,
                github_id=project.pk,
                name=f"repository-{project.pk}",
                full_name=f"example/repository-{project.pk}",
                html_url=f"https://github.com/example/repository-{project.pk}",
            )
            RepositoryStatus.objects.create(
                repository=repository,
                last_status_code="PENDING",
            )

        self.assertTrue(has_pending_project_ranking_refreshes())
        Project.objects.filter(status=Project.Status.ACTIVE).update(
            status=Project.Status.INACTIVE
        )
        self.assertFalse(has_pending_project_ranking_refreshes())

    @patch("rankings.tasks.calculate_project_rankings")
    @patch("rankings.tasks.has_pending_project_ranking_refreshes")
    def test_retries_while_repository_refresh_is_pending(
        self,
        has_pending_refreshes,
        calculate_rankings,
    ):
        has_pending_refreshes.return_value = True

        with (
            patch.object(
                calculate_daily_project_rankings,
                "retry",
                side_effect=Retry(),
            ) as retry,
            self.assertRaises(Retry),
        ):
            calculate_daily_project_rankings.run(period_end="2026-08-13")

        retry.assert_called_once_with(countdown=RANKING_RETRY_DELAY_SECONDS)
        calculate_rankings.assert_not_called()

    @patch("rankings.tasks.calculate_project_rankings")
    @patch("rankings.tasks.has_pending_project_ranking_refreshes")
    def test_calculates_when_repository_refresh_is_complete(
        self,
        has_pending_refreshes,
        calculate_rankings,
    ):
        has_pending_refreshes.return_value = False
        calculate_rankings.return_value.pk = 17

        run_id = calculate_daily_project_rankings.run(
            period_end="2026-08-13"
        )

        self.assertEqual(run_id, 17)
        calculate_rankings.assert_called_once_with(date(2026, 8, 13))

    def test_retry_policy_is_limited_to_two_hours(self):
        self.assertEqual(
            calculate_daily_project_rankings.max_retries,
            RANKING_MAX_RETRIES,
        )
        self.assertEqual(
            RANKING_RETRY_DELAY_SECONDS * RANKING_MAX_RETRIES,
            2 * 60 * 60,
        )
