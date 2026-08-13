from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from projects.models import Project, Repository, RepositorySnapshot

from .models import (
    ProjectRankingResult,
    ProjectRankingRun,
    ProjectRankingWeight,
)
from .services import calculate_project_rankings


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
        changed: bool,
    ) -> None:
        RepositorySnapshot.objects.create(
            repository=repository,
            date=snapshot_date,
            stars=stars,
            forks=forks,
            commits=commits,
            pull_requests=pull_requests,
            has_code_changed=changed,
        )

    def test_calculates_deltas_activity_and_streaks(self):
        repository = self.create_repository_project(name="계산 프로젝트")
        snapshots = (
            (date(2025, 8, 13), 10, 2, 20, 3, False),
            (date(2026, 8, 10), 12, 3, 25, 5, True),
            (date(2026, 8, 11), 13, 3, 26, 5, True),
            (date(2026, 8, 12), 14, 4, 30, 6, False),
            (date(2026, 8, 13), 15, 4, 35, 7, True),
        )
        for snapshot in snapshots:
            self.create_snapshot(
                repository,
                snapshot[0],
                stars=snapshot[1],
                forks=snapshot[2],
                commits=snapshot[3],
                pull_requests=snapshot[4],
                changed=snapshot[5],
            )

        run = calculate_project_rankings(date(2026, 8, 13))

        result = run.results.get(project=repository.project)
        self.assertEqual(run.period_start, date(2025, 8, 13))
        self.assertEqual(result.actual_period_start, date(2025, 8, 13))
        self.assertEqual(result.stars, 5)
        self.assertEqual(result.forks, 2)
        self.assertEqual(result.commits, 15)
        self.assertEqual(result.pull_requests, 4)
        self.assertEqual(result.active_days, 3)
        self.assertEqual(result.max_streak, 2)
        self.assertEqual(result.current_streak, 1)
        self.assertEqual(result.total_score, Decimal("31.00"))

    def test_uses_first_available_snapshot_for_short_history(self):
        repository = self.create_repository_project(name="신규 프로젝트")
        self.create_snapshot(
            repository,
            date(2026, 8, 12),
            stars=10,
            forks=2,
            commits=5,
            pull_requests=1,
            changed=True,
        )
        self.create_snapshot(
            repository,
            date(2026, 8, 13),
            stars=11,
            forks=2,
            commits=7,
            pull_requests=2,
            changed=True,
        )

        result = calculate_project_rankings(date(2026, 8, 13)).results.get()

        self.assertEqual(result.actual_period_start, date(2026, 8, 12))
        self.assertEqual(result.stars, 1)
        self.assertEqual(result.commits, 2)
        self.assertEqual(result.pull_requests, 1)
        self.assertEqual(result.active_days, 2)
        self.assertEqual(result.max_streak, 2)

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
            changed=True,
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
                changed=False,
            )
            self.create_snapshot(
                repository,
                date(2026, 8, 13),
                stars=stars,
                forks=0,
                commits=0,
                pull_requests=0,
                changed=False,
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
            changed=False,
        )
        self.create_snapshot(
            repository,
            date(2026, 8, 13),
            stars=100,
            forks=0,
            commits=2,
            pull_requests=0,
            changed=False,
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
            changed=False,
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
            active_days_weight=Decimal("1.00"),
            max_streak_weight=Decimal("1.00"),
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
            active_days=4,
            max_streak=2,
            current_streak=1,
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
