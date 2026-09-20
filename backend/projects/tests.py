from datetime import date, timedelta
from unittest.mock import ANY, Mock, patch

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import (
    Member,
    Project,
    ProjectLanguage,
    Repository,
    RepositoryLanguage,
    RepositorySnapshot,
    RepositoryStatus,
)
from .serializers import ProjectDetailSerializer, RepositorySerializer
from .tasks import (
    GITHUB_API_FAILED,
    PENDING,
    REFRESH_SKIPPED,
    SUCCESS,
    enqueue_daily_repository_refreshes,
    refresh_repository,
)


class RepositoryDataModelTests(TestCase):
    def setUp(self):
        project = Project.objects.create(
            name="Repository Data Project",
            description="Repository 수집 데이터 모델 검증",
        )
        self.repository = Repository.objects.create(
            project=project,
            github_id=9001,
            name="repository-data",
            full_name="example/repository-data",
            html_url="https://github.com/example/repository-data",
        )

    def test_repository_data_constraints_and_defaults(self):
        snapshot = RepositorySnapshot.objects.create(
            repository=self.repository,
            date=date(2026, 7, 28),
        )
        language = RepositoryLanguage.objects.create(
            repository=self.repository,
            language="Python",
        )
        status = RepositoryStatus.objects.create(
            repository=self.repository,
            last_status_code="SUCCESS",
        )

        self.assertEqual(snapshot.pull_requests, 0)
        self.assertEqual(snapshot.commits, 0)
        self.assertEqual(snapshot.stars, 0)
        self.assertEqual(snapshot.forks, 0)
        self.assertFalse(snapshot.has_code_changed)
        self.assertEqual(language.bytes, 0)
        self.assertEqual(status.current_streak, 0)
        self.assertEqual(status.max_streak, 0)
        self.assertIsNone(status.description)
        self.assertIsNone(status.fetched_at)

        with self.assertRaises(IntegrityError), transaction.atomic():
            RepositorySnapshot.objects.create(
                repository=self.repository,
                date=snapshot.date,
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            RepositoryLanguage.objects.create(
                repository=self.repository,
                language=language.language,
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            RepositoryStatus.objects.create(
                repository=self.repository,
                last_status_code="SUCCESS",
            )

    def test_project_becomes_inactive_after_30_normal_inactive_snapshots(self):
        snapshot_date = date(2026, 7, 28)
        RepositorySnapshot.objects.bulk_create(
            [
                RepositorySnapshot(
                    repository=self.repository,
                    date=snapshot_date - timedelta(days=offset),
                )
                for offset in range(30)
            ]
        )

        changed = self.repository.project.deactivate_if_repository_inactive(
            snapshot_date
        )

        self.assertTrue(changed)
        self.assertEqual(
            self.repository.project.status,
            Project.Status.INACTIVE,
        )
        self.repository.project.save(update_fields=("status", "updated_at"))
        self.repository.project.refresh_from_db()
        self.assertEqual(
            self.repository.project.status,
            Project.Status.INACTIVE,
        )

    def test_project_stays_active_when_snapshot_dates_have_a_gap(self):
        snapshot_date = date(2026, 7, 28)
        RepositorySnapshot.objects.bulk_create(
            [
                RepositorySnapshot(
                    repository=self.repository,
                    date=snapshot_date - timedelta(days=offset),
                )
                for offset in range(31)
                if offset != 10
            ]
        )

        changed = self.repository.project.deactivate_if_repository_inactive(
            snapshot_date
        )

        self.assertFalse(changed)
        self.repository.project.refresh_from_db()
        self.assertEqual(self.repository.project.status, Project.Status.ACTIVE)

    def test_repository_serializer_does_not_query_fallback_relations(self):
        self.repository.serialized_status = None
        self.repository.serialized_snapshots = []
        self.repository.serialized_languages = []

        with self.assertNumQueries(0):
            data = RepositorySerializer(self.repository).data

        self.assertEqual(data["stars"], 0)
        self.assertEqual(data["forks"], 0)
        self.assertEqual(data["languages"], [])
        self.assertNotIn("language", data)


class RepositoryRefreshTaskTests(TestCase):
    def setUp(self):
        project = Project.objects.create(
            name="Repository Refresh Project",
            description="Repository 수집 작업 검증",
        )
        self.repository = Repository.objects.create(
            project=project,
            github_id=9001,
            name="repository-data",
            full_name="example/repository-data",
            html_url="https://github.com/example/repository-data",
        )

    def response(self, data, status_code=200, headers=None):
        response = Mock()
        response.status_code = status_code
        response.headers = headers or {}
        response.links = {}
        response.json.return_value = data
        return response

    def successful_responses(self, languages):
        commit_response = self.response([{"sha": "commit-1"}])
        commit_response.links = {
            "last": {
                "url": (
                    "https://api.github.com/repositories/9001/commits"
                    "?sha=main&per_page=1&page=17"
                )
            }
        }
        responses = [
            self.response(
                {
                    "id": 9001,
                    "name": "repository-data",
                    "full_name": "example/repository-data",
                    "html_url": "https://github.com/example/repository-data",
                    "description": "수집된 설명",
                    "private": False,
                    "default_branch": "main",
                    "stargazers_count": 12,
                    "forks_count": 3,
                }
            ),
            self.response(languages),
            commit_response,
            self.response({"total_count": 23, "incomplete_results": False}),
        ]
        return responses

    @patch("projects.tasks.refresh_repository.delay")
    def test_daily_refresh_enqueues_only_active_repositories_without_snapshot(
        self,
        refresh_delay,
    ):
        snapshot_date = date(2026, 7, 28)
        completed_project = Project.objects.create(
            name="Already Collected Project",
            description="당일 수집 완료 프로젝트",
        )
        completed_repository = Repository.objects.create(
            project=completed_project,
            github_id=9002,
            name="completed",
            full_name="example/completed",
            html_url="https://github.com/example/completed",
        )
        RepositorySnapshot.objects.create(
            repository=completed_repository,
            date=snapshot_date,
        )
        inactive_project = Project.objects.create(
            name="Inactive Repository Project",
            description="비활성 프로젝트",
            status=Project.Status.INACTIVE,
        )
        Repository.objects.create(
            project=inactive_project,
            github_id=9003,
            name="inactive",
            full_name="example/inactive",
            html_url="https://github.com/example/inactive",
        )

        with self.captureOnCommitCallbacks(execute=True):
            scheduled_count = enqueue_daily_repository_refreshes(
                snapshot_date.isoformat()
            )

        self.assertEqual(scheduled_count, 1)
        refresh_delay.assert_called_once_with(
            self.repository.pk,
            snapshot_date.isoformat(),
            ANY,
        )

    def test_repository_refresh_beat_schedule_runs_three_checks(self):
        refresh = settings.CELERY_BEAT_SCHEDULE["repository-refresh"]
        self.assertEqual(
            refresh["task"],
            "projects.tasks.enqueue_daily_repository_refreshes",
        )
        self.assertEqual(refresh["schedule"].minute, {10})
        self.assertEqual(refresh["schedule"].hour, {0, 1, 2})

    def test_repository_refresh_task_has_configured_rate_limit(self):
        self.assertEqual(
            refresh_repository.rate_limit,
            settings.REPOSITORY_REFRESH_TASK_RATE_LIMIT,
        )

    @patch("projects.github_client.requests.get")
    def test_refresh_skips_non_active_projects(self, request_get):
        for project_status in (
            Project.Status.INACTIVE,
            Project.Status.FINISHED,
            Project.Status.DELETED,
        ):
            with self.subTest(project_status=project_status):
                self.repository.project.status = project_status
                self.repository.project.save(
                    update_fields=("status", "updated_at")
                )

                self.assertFalse(
                    refresh_repository(self.repository.pk, "2026-07-28")
                )

        request_get.assert_not_called()

    @patch("projects.tasks.collect_repository")
    def test_refresh_skips_save_when_project_becomes_inactive(
        self,
        collect_repository,
    ):
        def deactivate_project(_full_name, _github_id):
            Project.objects.filter(pk=self.repository.project_id).update(
                status=Project.Status.INACTIVE
            )
            return {}

        collect_repository.side_effect = deactivate_project

        self.assertFalse(refresh_repository(self.repository.pk, "2026-07-28"))
        self.assertFalse(self.repository.snapshots.exists())

    @patch("projects.github_client.requests.get")
    def test_skipped_refresh_clears_current_pending_status(self, request_get):
        repository_status = RepositoryStatus.objects.create(
            repository=self.repository,
            last_status_code=PENDING,
        )
        requested_at = repository_status.updated_at.isoformat()
        self.repository.project.status = Project.Status.FINISHED
        self.repository.project.save(update_fields=("status", "updated_at"))

        self.assertFalse(
            refresh_repository(
                self.repository.pk,
                "2026-07-28",
                requested_at,
            )
        )

        repository_status.refresh_from_db()
        self.assertEqual(
            repository_status.last_status_code,
            REFRESH_SKIPPED,
        )
        request_get.assert_not_called()

    @patch("projects.github_client.requests.get", side_effect=requests.RequestException)
    def test_superseded_failure_does_not_overwrite_newer_status(
        self,
        request_get,
    ):
        repository_status = RepositoryStatus.objects.create(
            repository=self.repository,
            last_status_code=PENDING,
        )
        old_requested_at = repository_status.updated_at.isoformat()
        RepositoryStatus.objects.filter(repository=self.repository).update(
            updated_at=timezone.now() + timedelta(seconds=1)
        )

        self.assertFalse(
            refresh_repository(
                self.repository.pk,
                "2026-07-28",
                old_requested_at,
            )
        )

        repository_status.refresh_from_db()
        self.assertEqual(repository_status.last_status_code, PENDING)
        request_get.assert_called_once()

    @patch("projects.github_client.requests.get")
    def test_superseded_success_does_not_overwrite_newer_request(
        self,
        request_get,
    ):
        repository_status = RepositoryStatus.objects.create(
            repository=self.repository,
            last_status_code=PENDING,
        )
        old_requested_at = repository_status.updated_at.isoformat()
        RepositoryStatus.objects.filter(repository=self.repository).update(
            updated_at=timezone.now() + timedelta(seconds=1)
        )
        request_get.side_effect = self.successful_responses({"Python": 100})

        self.assertFalse(
            refresh_repository(
                self.repository.pk,
                "2026-07-28",
                old_requested_at,
            )
        )

        repository_status.refresh_from_db()
        self.assertEqual(repository_status.last_status_code, PENDING)
        self.assertFalse(self.repository.snapshots.exists())

    @patch("projects.github_client.requests.get")
    def test_refresh_saves_normalized_collection(self, request_get):
        request_get.side_effect = self.successful_responses(
            {"Python": 100, "JavaScript": 50}
        )

        result = refresh_repository(self.repository.pk, "2026-07-28")

        self.assertTrue(result)
        snapshot = self.repository.snapshots.get(date=date(2026, 7, 28))
        self.assertEqual(snapshot.stars, 12)
        self.assertEqual(snapshot.forks, 3)
        self.assertEqual(snapshot.commits, 17)
        self.assertEqual(snapshot.pull_requests, 23)
        self.assertTrue(snapshot.has_code_changed)
        self.assertEqual(
            request_get.call_args_list[2].kwargs["params"],
            {"sha": "main", "per_page": 1},
        )
        self.assertEqual(
            request_get.call_args_list[3].kwargs["params"],
            {
                "q": "repo:example/repository-data is:pr",
                "per_page": 1,
            },
        )
        self.assertEqual(
            dict(self.repository.languages.values_list("language", "bytes")),
            {"Python": 100, "JavaScript": 50},
        )
        status = self.repository.status
        self.assertEqual(status.description, "수집된 설명")
        self.assertEqual(status.last_status_code, SUCCESS)
        self.assertEqual(status.current_streak, 1)
        self.assertEqual(status.max_streak, 1)
        self.assertIsNotNone(status.fetched_at)

    @patch("projects.github_client.requests.get")
    def test_refresh_detects_language_change_and_updates_streak(self, request_get):
        RepositorySnapshot.objects.create(
            repository=self.repository,
            date=date(2026, 7, 27),
            has_code_changed=True,
        )
        RepositoryStatus.objects.create(
            repository=self.repository,
            last_status_code=SUCCESS,
            current_streak=1,
            max_streak=1,
        )
        RepositoryLanguage.objects.create(
            repository=self.repository,
            language="Python",
            bytes=100,
        )
        request_get.side_effect = self.successful_responses(
            {"Python": 80, "Go": 20}
        )

        self.assertTrue(refresh_repository(self.repository.pk, "2026-07-28"))

        snapshot = self.repository.snapshots.get(date=date(2026, 7, 28))
        self.assertTrue(snapshot.has_code_changed)
        self.repository.status.refresh_from_db()
        self.assertEqual(self.repository.status.current_streak, 2)
        self.assertEqual(self.repository.status.max_streak, 2)
        self.assertEqual(
            dict(self.repository.languages.values_list("language", "bytes")),
            {"Python": 80, "Go": 20},
        )

    @patch("projects.github_client.requests.get")
    def test_same_day_refresh_does_not_erase_detected_code_change(
        self,
        request_get,
    ):
        RepositorySnapshot.objects.create(
            repository=self.repository,
            date=date(2026, 7, 28),
            has_code_changed=True,
        )
        RepositoryLanguage.objects.create(
            repository=self.repository,
            language="Python",
            bytes=100,
        )
        request_get.side_effect = self.successful_responses({"Python": 100})

        self.assertTrue(refresh_repository(self.repository.pk, "2026-07-28"))

        snapshot = self.repository.snapshots.get(date=date(2026, 7, 28))
        self.assertTrue(snapshot.has_code_changed)

    @patch("projects.github_client.requests.get")
    def test_same_day_code_change_recalculates_streak(self, request_get):
        RepositorySnapshot.objects.bulk_create(
            [
                RepositorySnapshot(
                    repository=self.repository,
                    date=date(2026, 7, 26),
                    has_code_changed=True,
                ),
                RepositorySnapshot(
                    repository=self.repository,
                    date=date(2026, 7, 27),
                    has_code_changed=True,
                ),
                RepositorySnapshot(
                    repository=self.repository,
                    date=date(2026, 7, 28),
                    has_code_changed=False,
                ),
            ]
        )
        RepositoryStatus.objects.create(
            repository=self.repository,
            last_status_code=SUCCESS,
            current_streak=0,
            max_streak=2,
        )
        RepositoryLanguage.objects.create(
            repository=self.repository,
            language="Python",
            bytes=100,
        )
        request_get.side_effect = self.successful_responses({"Python": 80})

        self.assertTrue(refresh_repository(self.repository.pk, "2026-07-28"))

        self.repository.status.refresh_from_db()
        self.assertEqual(self.repository.status.current_streak, 3)
        self.assertEqual(self.repository.status.max_streak, 3)

    @patch("projects.github_client.requests.get")
    def test_incomplete_pull_request_results_preserve_last_collection(
        self,
        request_get,
    ):
        snapshot = RepositorySnapshot.objects.create(
            repository=self.repository,
            date=date(2026, 7, 27),
            stars=7,
        )
        request_get.side_effect = [
            *self.successful_responses({"Python": 100})[:-1],
            self.response({"total_count": 2, "incomplete_results": True}),
        ]

        self.assertFalse(refresh_repository(self.repository.pk, "2026-07-28"))

        snapshot.refresh_from_db()
        self.repository.status.refresh_from_db()
        self.assertEqual(snapshot.stars, 7)
        self.assertFalse(
            self.repository.snapshots.filter(date=date(2026, 7, 28)).exists()
        )
        self.assertEqual(
            self.repository.status.last_status_code,
            GITHUB_API_FAILED,
        )

    @patch("projects.github_client.requests.get")
    def test_refresh_failure_preserves_last_normal_collection(self, request_get):
        snapshot = RepositorySnapshot.objects.create(
            repository=self.repository,
            date=date(2026, 7, 27),
            stars=7,
        )
        language = RepositoryLanguage.objects.create(
            repository=self.repository,
            language="Python",
            bytes=100,
        )
        fetched_at = timezone.now() - timedelta(days=1)
        RepositoryStatus.objects.create(
            repository=self.repository,
            description="기존 설명",
            last_status_code=SUCCESS,
            fetched_at=fetched_at,
        )
        request_get.side_effect = requests.RequestException

        self.assertFalse(refresh_repository(self.repository.pk, "2026-07-28"))

        snapshot.refresh_from_db()
        language.refresh_from_db()
        self.repository.status.refresh_from_db()
        self.assertEqual(snapshot.stars, 7)
        self.assertEqual(language.bytes, 100)
        self.assertEqual(self.repository.status.description, "기존 설명")
        self.assertEqual(
            self.repository.status.last_status_code,
            GITHUB_API_FAILED,
        )
        self.assertEqual(self.repository.status.fetched_at, fetched_at)


class ProjectApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="jiyeon",
            password="password",
            github_email="0215wldus@sookmyung.ac.kr",
            name="권지연",
            student_id=215,
            major="IT공학",
        )
        self.project = Project.objects.create(
            name="SOSP",
            description="SMU Open-Source Platform",
            demo_url="https://sosp.sookmyung.ac.kr",
            status=Project.Status.ACTIVE,
        )
        self.project.languages.set(
            ProjectLanguage.objects.filter(name__in=("Python", "TypeScript"))
        )
        self.repository = Repository.objects.create(
            project=self.project,
            github_id=101,
            name="SMU-OSP",
            full_name="Jiyeon125/SMU-OSP",
            html_url="https://github.com/Jiyeon125/SMU-OSP",
        )
        self.member = Member.objects.create(
            project=self.project,
            user=self.user,
            is_leader=True,
            status=Member.Status.JOINED,
        )

    def test_member_table_uses_id_primary_key_with_project_id_unique_constraint(
        self,
    ):
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor,
                Member._meta.db_table,
            )

        primary_key = next(
            constraint
            for constraint in constraints.values()
            if constraint["primary_key"]
        )
        self.assertEqual(primary_key["columns"], ["id"])

        project_id_unique = constraints["project_member_project_id_uniq"]
        self.assertTrue(project_id_unique["unique"])
        self.assertEqual(project_id_unique["columns"], ["project_id", "id"])

    def test_member_canceled_status_is_persisted(self):
        canceled_member = Member.objects.create(
            project=self.project,
            user=self.user,
            status=Member.Status.CANCELED,
        )

        canceled_member.refresh_from_db()
        self.assertEqual(canceled_member.status, Member.Status.CANCELED)

    @override_settings(PROJECT_DEFAULT_MAX_MEMBERS=7)
    def test_project_default_max_members_uses_setting(self):
        project = Project.objects.create(
            name="Configured Capacity Project",
            description="환경변수 기반 기본 최대 인원을 확인합니다.",
        )

        self.assertEqual(project.max_members, 7)

    def test_project_list_response_shape(self):
        response = self.client.get("/api/v1/projects/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(len(body["data"]), 1)
        self.assertEqual(body["data"][0]["name"], "SOSP")
        self.assertNotIn("teamName", body["data"][0])
        self.assertNotIn("teamId", body["data"][0])
        self.assertNotIn("leaderId", body["data"][0])
        self.assertNotIn("repositoryId", body["data"][0])
        self.assertNotIn("repositoryUrl", body["data"][0])
        self.assertNotIn("demoUrl", body["data"][0])
        self.assertNotIn("presentationUrl", body["data"][0])
        self.assertNotIn("maxMembers", body["data"][0])
        self.assertEqual(body["data"][0]["status"], "ACTIVE")
        self.assertIsNone(body["data"][0]["membershipRole"])
        repository = body["data"][0]["repository"]
        self.assertEqual(repository["fullName"], "Jiyeon125/SMU-OSP")
        self.assertNotIn("id", repository)
        self.assertNotIn("githubId", repository)
        self.assertNotIn("name", repository)
        self.assertNotIn("description", repository)
        self.assertNotIn("language", repository)
        self.assertEqual(body["detail"]["pagination"]["count"], 1)
        self.assertEqual(body["detail"]["pagination"]["currentPage"], 1)

    def test_project_language_list_uses_programming_languages(self):
        response = self.client.get("/api/v1/projects/languages")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Python", response.json()["data"])
        self.assertIn("TypeScript", response.json()["data"])
        self.assertNotIn("React", response.json()["data"])
        self.assertNotIn("Django", response.json()["data"])

    def test_project_create_normalizes_and_rejects_language_names(self):
        self.client.force_login(self.user)
        payload = {
            "name": "Language Project",
            "description": "사용 언어 검증",
            "techStack": ["python", "PYTHON", "TypeScript"],
        }

        response = self.client.post(
            "/api/v1/projects/",
            data=payload,
            content_type="application/json",
        )
        invalid_response = self.client.post(
            "/api/v1/projects/",
            data={**payload, "name": "Framework Project", "techStack": ["React"]},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        project = Project.objects.get(name="Language Project")
        self.assertEqual(response.json()["data"], {"id": project.pk})
        self.assertEqual(
            list(project.languages.values_list("name", flat=True)),
            ["Python", "TypeScript"],
        )
        self.assertEqual(invalid_response.status_code, 400)
        self.assertIn(
            "등록 가능한 프로그래밍 언어",
            invalid_response.json()["detail"]["message"],
        )

    def test_project_list_separates_finished_and_hides_deleted_projects(self):
        finished_owned = Project.objects.create(
            name="Finished Owned Project",
            description="완료된 팀장 프로젝트",
            status=Project.Status.FINISHED,
        )
        Member.objects.create(
            project=finished_owned,
            user=self.user,
            is_leader=True,
            status=Member.Status.JOINED,
        )
        other_user = get_user_model().objects.create_user(
            username="finished-leader",
            github_email="finished-leader@example.com",
            name="완료 프로젝트 팀장",
            student_id=300,
            major="IT공학",
        )
        finished_joined = Project.objects.create(
            name="Finished Joined Project",
            description="완료된 팀원 프로젝트",
            status=Project.Status.FINISHED,
        )
        Member.objects.create(
            project=finished_joined,
            user=other_user,
            is_leader=True,
            status=Member.Status.JOINED,
        )
        Member.objects.create(
            project=finished_joined,
            user=self.user,
            status=Member.Status.JOINED,
        )
        deleted = Project.objects.create(
            name="Deleted Project",
            description="삭제된 프로젝트",
            status=Project.Status.DELETED,
        )
        Member.objects.create(
            project=deleted,
            user=self.user,
            is_leader=True,
            status=Member.Status.JOINED,
        )

        default_response = self.client.get("/api/v1/projects/")
        self.client.force_login(self.user)
        finished_response = self.client.get(
            "/api/v1/projects/?joined=true&owned=true&status=FINISHED"
        )
        finished_owned_response = self.client.get(
            "/api/v1/projects/?owned=true&status=FINISHED"
        )
        finished_joined_response = self.client.get(
            "/api/v1/projects/?joined=true&status=FINISHED"
        )

        self.assertEqual(
            [project["name"] for project in default_response.json()["data"]],
            ["SOSP"],
        )
        self.assertEqual(finished_response.status_code, 200)
        self.assertEqual(
            {
                project["name"]: project["membershipRole"]
                for project in finished_response.json()["data"]
            },
            {
                "Finished Owned Project": "OWNER",
                "Finished Joined Project": "MEMBER",
            },
        )
        self.assertEqual(
            [
                project["name"]
                for project in finished_owned_response.json()["data"]
            ],
            ["Finished Owned Project"],
        )
        self.assertEqual(
            [
                project["name"]
                for project in finished_joined_response.json()["data"]
            ],
            ["Finished Joined Project"],
        )

    def test_finished_project_list_requires_login(self):
        response = self.client.get(
            "/api/v1/projects/?joined=true&owned=true&status=FINISHED"
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "PERMISSION_DENIED")

    def test_project_detail_response_shape(self):
        response = self.client.get(f"/api/v1/projects/{self.project.pk}")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(body["data"]["id"], self.project.pk)
        self.assertEqual(
            body["data"]["repository"]["htmlUrl"],
            "https://github.com/Jiyeon125/SMU-OSP",
        )
        self.assertEqual(body["data"]["memberCount"], 1)
        self.assertFalse(body["data"]["canViewMembers"])
        self.assertFalse(body["data"]["canEdit"])
        self.assertFalse(body["data"]["canApply"])
        self.assertIsNone(body["data"]["applicationStatus"])
        self.assertEqual(body["data"]["pendingMemberCount"], 0)
        self.assertIsNone(body["data"]["members"])

    def test_project_detail_serializer_does_not_query_member_fallback(self):
        serializer = ProjectDetailSerializer(
            self.project,
            context={"can_view_members": True},
        )

        with self.assertNumQueries(0):
            members = serializer.get_members(self.project)

        self.assertEqual(members, [])

    def test_project_detail_returns_pending_count_only_to_leader(self):
        applicant = get_user_model().objects.create_user(
            username="pending-count-applicant",
            github_email="pending-count-applicant@example.com",
            name="대기 신청자",
            student_id=302,
            major="IT공학",
        )
        Member.objects.create(
            project=self.project,
            user=applicant,
            status=Member.Status.PENDING,
        )
        self.client.force_login(self.user)

        response = self.client.get(f"/api/v1/projects/{self.project.pk}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["pendingMemberCount"], 1)

        self.client.force_login(applicant)
        response = self.client.get(f"/api/v1/projects/{self.project.pk}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["pendingMemberCount"], 0)

    def test_project_detail_allows_eligible_user_to_apply(self):
        applicant = get_user_model().objects.create_user(
            username="eligible-applicant",
            github_email="eligible-applicant@example.com",
            name="신규 신청자",
            student_id=303,
            major="IT공학",
        )
        self.client.force_login(applicant)

        response = self.client.get(f"/api/v1/projects/{self.project.pk}")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["data"]["canApply"])

    def test_project_detail_returns_current_application_state(self):
        applicant = get_user_model().objects.create_user(
            username="detail-applicant",
            github_email="detail-applicant@example.com",
            name="신청자",
            student_id=301,
            major="IT공학",
        )
        Member.objects.create(
            project=self.project,
            user=applicant,
            status=Member.Status.CANCELED,
        )
        latest_application = Member.objects.create(
            project=self.project,
            user=applicant,
            status=Member.Status.PENDING,
        )
        self.client.force_login(applicant)

        response = self.client.get(f"/api/v1/projects/{self.project.pk}")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(
            data["applicationStatus"],
            latest_application.status,
        )
        self.assertFalse(data["canApply"])

    def test_deleted_project_detail_is_not_available(self):
        self.project.status = Project.Status.DELETED
        self.project.save(update_fields=("status", "updated_at"))

        response = self.client.get(f"/api/v1/projects/{self.project.pk}")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["status"], "PROJECT_NOT_FOUND")

    def test_project_detail_uses_normalized_repository_data(self):
        RepositorySnapshot.objects.create(
            repository=self.repository,
            date=date(2026, 7, 27),
            stars=12,
            forks=3,
        )
        RepositoryLanguage.objects.create(
            repository=self.repository,
            language="Python",
            bytes=100,
        )
        fetched_at = timezone.now() - timedelta(days=1)
        RepositoryStatus.objects.create(
            repository=self.repository,
            description="정규화된 설명",
            last_status_code=SUCCESS,
            fetched_at=fetched_at,
        )

        response = self.client.get(f"/api/v1/projects/{self.project.pk}")

        repository = response.json()["data"]["repository"]
        self.assertEqual(repository["description"], "정규화된 설명")
        self.assertEqual(repository["stars"], 12)
        self.assertEqual(repository["forks"], 3)
        self.assertEqual(repository["languages"], ["Python"])
        self.assertNotIn("language", repository)
        self.assertNotIn("id", repository)
        self.assertNotIn("githubId", repository)
        self.assertNotIn("name", repository)
        self.assertNotIn("topics", repository)
        self.assertNotIn("lastStatusCode", repository)
        self.assertNotIn("statusUpdatedAt", repository)
        self.assertEqual(
            repository["fetchedAt"],
            fetched_at.isoformat().replace("+00:00", "Z"),
        )
        self.assertNotIn("refreshStatus", repository)
        self.assertNotIn("lastErrorCode", repository)

    def test_project_member_can_view_joined_member_details(self):
        teammate = get_user_model().objects.create_user(
            username="teammate",
            password="password",
            github_email="teammate@sookmyung.ac.kr",
            name="임꺽정",
            student_id=216,
            major="컴퓨터과학",
        )
        Member.objects.create(
            project=self.project,
            user=teammate,
            status=Member.Status.JOINED,
            description="프론트엔드",
        )
        self.client.force_login(self.user)

        response = self.client.get(f"/api/v1/projects/{self.project.pk}")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["memberCount"], 2)
        self.assertEqual(data["membershipRole"], "OWNER")
        self.assertTrue(data["canViewMembers"])
        self.assertTrue(data["canEdit"])
        self.assertEqual(
            [(member["name"], member["role"]) for member in data["members"]],
            [("권지연", "LEADER"), ("임꺽정", "MEMBER")],
        )
        self.assertEqual(data["members"][1]["username"], "teammate")
        self.assertIn("joinedAt", data["members"][1])
        for field in ("userId", "status", "description", "createdAt"):
            self.assertNotIn(field, data["members"][1])

    def test_inactive_project_leader_cannot_edit_project(self):
        self.project.status = Project.Status.INACTIVE
        self.project.save(update_fields=("status", "updated_at"))
        self.client.force_login(self.user)

        response = self.client.get(f"/api/v1/projects/{self.project.pk}")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertTrue(data["canViewMembers"])
        self.assertFalse(data["canEdit"])

    def test_applicant_can_only_view_joined_member_count(self):
        applicant = get_user_model().objects.create_user(
            username="applicant",
            password="password",
            github_email="applicant@sookmyung.ac.kr",
            name="신청자",
            student_id=217,
            major="소프트웨어학부",
        )
        Member.objects.create(
            project=self.project,
            user=applicant,
            status=Member.Status.PENDING,
        )
        self.client.force_login(applicant)

        response = self.client.get(f"/api/v1/projects/{self.project.pk}")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["memberCount"], 1)
        self.assertFalse(data["canViewMembers"])
        self.assertFalse(data["canEdit"])
        self.assertIsNone(data["members"])

    def test_project_leader_can_update_project_fields(self):
        self.client.force_login(self.user)

        response = self.client.put(
            f"/api/v1/projects/{self.project.pk}",
            data=self.project_update_payload(
                name="Updated SOSP",
                description="수정된 프로젝트 설명",
                demoUrl="https://updated.example.com",
                presentationUrl="https://updated.example.com/slides",
                techStack=["TypeScript", "Python", "Go"],
                status=Project.Status.FINISHED,
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertIsNone(body["data"])

        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Updated SOSP")
        self.assertEqual(self.project.status, Project.Status.FINISHED)
        self.assertEqual(self.project.max_members, 5)
        self.assertEqual(self.project.description, "수정된 프로젝트 설명")
        self.assertEqual(self.project.demo_url, "https://updated.example.com")
        self.assertEqual(
            self.project.presentation_url,
            "https://updated.example.com/slides",
        )
        self.assertEqual(
            list(self.project.languages.values_list("name", flat=True)),
            ["Go", "Python", "TypeScript"],
        )
        self.repository.refresh_from_db()
        self.assertEqual(
            self.repository.html_url,
            "https://github.com/Jiyeon125/SMU-OSP",
        )
        self.assertEqual(self.repository.github_id, 101)

    def test_project_leader_cannot_remove_repository_connection(self):
        self.client.force_login(self.user)

        response = self.client.put(
            f"/api/v1/projects/{self.project.pk}",
            data=self.project_update_payload(repositoryUrl=""),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "INVALID_PROJECT_INPUT")
        self.assertEqual(
            response.json()["detail"]["message"],
            "이미 등록된 Repository는 변경하거나 연결 해제할 수 없습니다.",
        )
        self.assertTrue(Repository.objects.filter(project=self.project).exists())

    def test_project_leader_cannot_change_repository_connection(self):
        self.client.force_login(self.user)

        response = self.client.put(
            f"/api/v1/projects/{self.project.pk}",
            data=self.project_update_payload(
                name="롤백되어야 하는 이름",
                repositoryUrl="https://github.com/example/other-project",
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"]["message"],
            "이미 등록된 Repository는 변경하거나 연결 해제할 수 없습니다.",
        )
        self.project.refresh_from_db()
        self.repository.refresh_from_db()
        self.assertEqual(self.project.name, "SOSP")
        self.assertEqual(
            self.repository.html_url,
            "https://github.com/Jiyeon125/SMU-OSP",
        )

    def test_non_leader_cannot_update_project(self):
        teammate = get_user_model().objects.create_user(
            username="nonleader",
            password="password",
            github_email="nonleader@sookmyung.ac.kr",
            name="팀원",
            student_id=218,
            major="컴퓨터과학",
        )
        Member.objects.create(
            project=self.project,
            user=teammate,
            status=Member.Status.JOINED,
        )
        self.client.force_login(teammate)

        response = self.client.put(
            f"/api/v1/projects/{self.project.pk}",
            data=self.project_update_payload(name="권한 없는 수정"),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "PERMISSION_DENIED")
        self.assertEqual(
            response.json()["detail"]["message"],
            "프로젝트 접근 권한이 없습니다.",
        )
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "SOSP")

    def test_project_update_and_delete_require_login(self):
        update_response = self.client.put(
            f"/api/v1/projects/{self.project.pk}",
            data=self.project_update_payload(name="익명 수정"),
            content_type="application/json",
        )
        delete_response = self.client.delete(
            f"/api/v1/projects/{self.project.pk}"
        )

        for response in (update_response, delete_response):
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()["status"], "PERMISSION_DENIED")
            self.assertEqual(
                response.json()["detail"]["message"],
                "로그인이 필요합니다.",
            )

    def test_anonymous_user_cannot_use_orphaned_leader_membership(self):
        Member.objects.create(
            project=self.project,
            user=None,
            status=Member.Status.JOINED,
            is_leader=True,
        )

        response = self.client.put(
            f"/api/v1/projects/{self.project.pk}",
            data=self.project_update_payload(name="익명 수정"),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "PERMISSION_DENIED")
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "SOSP")

    def test_project_completion_cancels_pending_memberships(self):
        pending = Member.objects.create(
            project=self.project,
            status=Member.Status.PENDING,
        )
        self.client.force_login(self.user)

        response = self.client.put(
            f"/api/v1/projects/{self.project.pk}",
            data=self.project_update_payload(status=Project.Status.FINISHED),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        pending.refresh_from_db()
        self.assertEqual(pending.status, Member.Status.CANCELED)

    def test_project_leader_can_soft_delete_project(self):
        pending = Member.objects.create(
            project=self.project,
            status=Member.Status.PENDING,
        )
        self.client.force_login(self.user)

        response = self.client.delete(f"/api/v1/projects/{self.project.pk}")

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["data"])
        self.project.refresh_from_db()
        pending.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.DELETED)
        self.assertEqual(pending.status, Member.Status.CANCELED)
        self.assertTrue(Repository.objects.filter(project=self.project).exists())
        self.assertTrue(Member.objects.filter(project=self.project).exists())

        restore_response = self.client.put(
            f"/api/v1/projects/{self.project.pk}",
            data=self.project_update_payload(status=Project.Status.ACTIVE),
            content_type="application/json",
        )
        self.assertEqual(restore_response.status_code, 400)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.DELETED)

    def test_project_leader_can_soft_delete_finished_project(self):
        self.client.force_login(self.user)

        finish_response = self.client.put(
            f"/api/v1/projects/{self.project.pk}",
            data=self.project_update_payload(status=Project.Status.FINISHED),
            content_type="application/json",
        )
        delete_response = self.client.delete(
            f"/api/v1/projects/{self.project.pk}"
        )

        self.assertEqual(finish_response.status_code, 200)
        self.assertEqual(delete_response.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.DELETED)

    def test_non_leader_cannot_delete_project(self):
        teammate = get_user_model().objects.create_user(
            username="delete-nonleader",
            password="password",
            github_email="delete-nonleader@sookmyung.ac.kr",
            name="삭제 권한 없는 팀원",
            student_id=219,
            major="컴퓨터과학",
        )
        Member.objects.create(
            project=self.project,
            user=teammate,
            status=Member.Status.JOINED,
        )
        self.client.force_login(teammate)

        response = self.client.delete(f"/api/v1/projects/{self.project.pk}")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "PERMISSION_DENIED")
        self.assertEqual(
            response.json()["detail"]["message"],
            "프로젝트 접근 권한이 없습니다.",
        )
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.ACTIVE)

    def test_project_update_rejects_deleted_status(self):
        self.client.force_login(self.user)

        response = self.client.put(
            f"/api/v1/projects/{self.project.pk}",
            data=self.project_update_payload(status=Project.Status.DELETED),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "INVALID_PROJECT_INPUT")
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.ACTIVE)

    def test_finished_project_cannot_be_updated(self):
        self.project.status = Project.Status.FINISHED
        self.project.save(update_fields=["status"])
        self.client.force_login(self.user)

        response = self.client.put(
            f"/api/v1/projects/{self.project.pk}",
            data=self.project_update_payload(
                name="변경되면 안 되는 이름",
                status=Project.Status.FINISHED,
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "INVALID_PROJECT_INPUT")
        self.assertEqual(
            response.json()["detail"]["message"],
            "현재 프로젝트 상태에서는 수정할 수 없습니다.",
        )
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "SOSP")
        self.assertEqual(self.project.status, Project.Status.FINISHED)

    def test_project_update_rejects_another_project_name(self):
        Project.objects.create(name="Existing Project", description="기존 프로젝트")
        self.client.force_login(self.user)

        response = self.client.put(
            f"/api/v1/projects/{self.project.pk}",
            data=self.project_update_payload(name="Existing Project"),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "INVALID_PROJECT_INPUT")
        self.assertEqual(
            response.json()["detail"]["message"],
            "이미 등록된 프로젝트명입니다.",
        )

    def test_project_detail_not_found(self):
        response = self.client.get("/api/v1/projects/999")

        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertEqual(body["status"], "PROJECT_NOT_FOUND")
        self.assertIsNone(body["data"])
        self.assertEqual(body["detail"]["httpStatus"], 404)

    def test_project_update_and_delete_return_not_found(self):
        self.client.force_login(self.user)

        responses = (
            self.client.put(
                "/api/v1/projects/999",
                data=self.project_update_payload(),
                content_type="application/json",
            ),
            self.client.delete("/api/v1/projects/999"),
        )

        for response in responses:
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["status"], "PROJECT_NOT_FOUND")

    def test_project_delete_cascades_to_repository_and_members(self):
        repository_id = self.repository.pk
        member_id = self.member.pk

        Project.objects.filter(pk=self.project.pk).delete()

        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())
        self.assertFalse(Repository.objects.filter(pk=repository_id).exists())
        self.assertFalse(Member.objects.filter(pk=member_id).exists())

    @patch("projects.tasks.refresh_repository.delay")
    @patch("projects.github_client.requests.get")
    def test_create_project_creates_leader_member_and_repository(
        self,
        request_get,
        refresh_delay,
    ):
        request_get.return_value.status_code = 200
        request_get.return_value.json.return_value = {
            "id": 202,
            "name": "new-project",
            "full_name": "example/new-project",
            "html_url": "https://github.com/example/new-project",
            "private": False,
        }
        self.client.force_login(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                "/api/v1/projects/",
                data={
                    "name": "New Project",
                    "description": "프로젝트 정보만 입력해 등록합니다.",
                    "repositoryUrl": "https://github.com/example/new-project",
                    "demoUrl": "",
                    "presentationUrl": "",
                    "techStack": ["TypeScript", "Python"],
                },
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        created_project = Project.objects.get(name="New Project")
        self.assertEqual(body["data"], {"id": created_project.pk})
        self.assertEqual(created_project.max_members, 5)
        leader_member = created_project.members.get()
        self.assertEqual(leader_member.user, self.user)
        self.assertEqual(leader_member.status, Member.Status.JOINED)
        self.assertTrue(leader_member.is_leader)
        repository = created_project.repository
        self.assertEqual(repository.name, "new-project")
        self.assertEqual(repository.full_name, "example/new-project")
        self.assertEqual(
            repository.html_url,
            "https://github.com/example/new-project",
        )
        self.assertEqual(repository.github_id, 202)
        self.assertEqual(
            RepositoryStatus.objects.get(
                repository=repository
            ).last_status_code,
            PENDING,
        )
        refresh_delay.assert_called_once_with(repository.pk, ANY, ANY)

    def test_create_project_without_repository_url_keeps_repository_empty(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/v1/projects/",
            data={
                "name": "Project Without Repository",
                "description": "Repository URL은 선택 입력값입니다.",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        project = Project.objects.get(name="Project Without Repository")
        self.assertEqual(body["data"], {"id": project.pk})
        self.assertEqual(project.max_members, 5)
        self.assertFalse(Repository.objects.filter(project=project).exists())
        self.assertTrue(project.members.get().is_leader)

    @patch("projects.github_client.requests.get")
    def test_create_project_keeps_project_when_repository_lookup_fails(
        self,
        request_get,
    ):
        request_get.return_value.status_code = 404
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/v1/projects/",
            data={
                "name": "Invalid Repository Project",
                "description": "조회되지 않는 Repository는 등록하지 않습니다.",
                "repositoryUrl": "https://github.com/example/not-found",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(
            body["detail"]["repositoryRegistration"]["code"],
            "GITHUB_REPOSITORY_NOT_FOUND",
        )
        self.assertEqual(
            body["detail"]["repositoryRegistration"]["message"],
            "존재하는 공개 GitHub Repository URL을 입력해주세요.",
        )
        project = Project.objects.get(name="Invalid Repository Project")
        self.assertEqual(body["data"], {"id": project.pk})
        self.assertFalse(
            Repository.objects.filter(project=project).exists()
        )

    def test_create_project_keeps_project_when_repository_already_linked(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/v1/projects/",
            data={
                "name": "Duplicate Repository Project",
                "description": "이미 연결된 Repository를 사용할 수 없습니다.",
                "repositoryUrl": "https://github.com/jiyeon125/smu-osp",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(
            body["detail"]["repositoryRegistration"]["message"],
            "이미 다른 프로젝트에 연결된 Repository입니다.",
        )
        project = Project.objects.get(name="Duplicate Repository Project")
        self.assertEqual(body["data"]["id"], project.pk)
        self.assertFalse(
            Repository.objects.filter(project=project).exists()
        )

    @patch("projects.github_client.requests.get")
    def test_deleted_project_repository_cannot_be_reused(self, request_get):
        self.project.status = Project.Status.DELETED
        self.project.save(update_fields=("status", "updated_at"))
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/v1/projects/",
            data={
                "name": "Deleted Repository Reuse Project",
                "description": "삭제된 프로젝트의 Repository도 재사용하지 않습니다.",
                "repositoryUrl": self.repository.html_url,
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.json()["detail"]["repositoryRegistration"]["message"],
            "이미 다른 프로젝트에 연결된 Repository입니다.",
        )
        project = Project.objects.get(name="Deleted Repository Reuse Project")
        self.assertFalse(Repository.objects.filter(project=project).exists())
        self.assertTrue(
            Repository.objects.filter(
                project=self.project,
                github_id=self.repository.github_id,
            ).exists()
        )
        request_get.assert_not_called()

    @patch("projects.github_client.requests.get")
    def test_project_without_repository_can_add_one(
        self,
        request_get,
    ):
        request_get.return_value.status_code = 200
        request_get.return_value.json.return_value = {
            "id": 303,
            "name": "new-project",
            "full_name": "example/new-project",
            "html_url": "https://github.com/example/new-project",
            "private": False,
        }
        self.repository.delete()
        self.client.force_login(self.user)

        response = self.client.put(
            f"/api/v1/projects/{self.project.pk}",
            data=self.project_update_payload(
                repositoryUrl="https://github.com/example/new-project"
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        repository = Repository.objects.get(project=self.project)
        self.assertEqual(repository.github_id, 303)
        self.assertEqual(
            repository.html_url,
            "https://github.com/example/new-project",
        )

    @patch("projects.github_client.requests.get")
    def test_project_update_rolls_back_when_repository_lookup_fails(
        self,
        request_get,
    ):
        request_get.return_value.status_code = 404
        self.repository.delete()
        self.client.force_login(self.user)

        response = self.client.put(
            f"/api/v1/projects/{self.project.pk}",
            data=self.project_update_payload(
                name="롤백되어야 하는 이름",
                repositoryUrl="https://github.com/example/not-found",
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["status"],
            "GITHUB_REPOSITORY_NOT_FOUND",
        )
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "SOSP")
        self.assertFalse(Repository.objects.filter(project=self.project).exists())

    @patch("projects.github_client.requests.get")
    def test_unchanged_repository_does_not_request_github(self, request_get):
        self.client.force_login(self.user)

        response = self.client.put(
            f"/api/v1/projects/{self.project.pk}",
            data=self.project_update_payload(),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        request_get.assert_not_called()

    @patch("projects.tasks.refresh_repository.delay")
    def test_restoring_inactive_project_enqueues_repository_refresh(
        self,
        refresh_delay,
    ):
        self.project.status = Project.Status.INACTIVE
        self.project.save(update_fields=("status", "updated_at"))
        self.client.force_login(self.user)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.put(
                f"/api/v1/projects/{self.project.pk}",
                data=self.project_update_payload(status=Project.Status.ACTIVE),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()
        self.assertEqual(self.project.status, Project.Status.ACTIVE)
        self.assertEqual(self.repository.status.last_status_code, PENDING)
        refresh_delay.assert_called_once_with(self.repository.pk, ANY, ANY)

    @patch("projects.services.enqueue_repository_refresh")
    def test_restoring_inactive_project_defers_refresh_until_commit(
        self,
        enqueue_refresh,
    ):
        self.project.status = Project.Status.INACTIVE
        self.project.save(update_fields=("status", "updated_at"))
        self.client.force_login(self.user)

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            response = self.client.put(
                f"/api/v1/projects/{self.project.pk}",
                data=self.project_update_payload(status=Project.Status.ACTIVE),
                content_type="application/json",
            )
            enqueue_refresh.assert_not_called()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(callbacks), 1)
        callbacks[0]()
        enqueue_refresh.assert_called_once_with(self.repository.pk)

    def test_create_project_requires_login(self):
        response = self.client.post(
            "/api/v1/projects/",
            data={
                "name": "Anonymous Project",
                "description": "로그인 없이 등록할 수 없습니다.",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        body = response.json()
        self.assertEqual(body["status"], "PERMISSION_DENIED")

    def test_create_project_rejects_duplicate_name(self):
        self.client.force_login(self.user)
        member_count = Member.objects.count()
        repository_count = Repository.objects.count()

        response = self.client.post(
            "/api/v1/projects/",
            data={
                "name": "SOSP",
                "description": "이미 존재하는 프로젝트명입니다.",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["status"], "INVALID_PROJECT_INPUT")
        self.assertEqual(body["detail"]["message"], "이미 등록된 프로젝트명입니다.")
        self.assertEqual(Project.objects.filter(name="SOSP").count(), 1)
        self.assertEqual(Member.objects.count(), member_count)
        self.assertEqual(Repository.objects.count(), repository_count)

    def test_create_project_rolls_back_when_leader_member_creation_fails(self):
        self.client.force_login(self.user)

        with patch(
            "projects.services.Member.objects.create",
            side_effect=IntegrityError,
        ):
            response = self.client.post(
                "/api/v1/projects/",
                data={
                    "name": "Rollback Project",
                    "description": "멤버 생성 실패 시 프로젝트도 저장되지 않습니다.",
                },
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["detail"]["message"],
            "프로젝트를 생성하지 못했습니다.",
        )
        self.assertFalse(Project.objects.filter(name="Rollback Project").exists())

    @patch("projects.github_client.requests.get")
    def test_create_project_keeps_project_when_repository_creation_fails(
        self,
        request_get,
    ):
        request_get.return_value.status_code = 200
        request_get.return_value.json.return_value = {
            "id": 404,
            "name": "rollback",
            "full_name": "example/rollback",
            "html_url": "https://github.com/example/rollback",
            "private": False,
        }
        self.client.force_login(self.user)

        with patch(
            "projects.services.Repository.objects.create",
            side_effect=IntegrityError,
        ):
            response = self.client.post(
                "/api/v1/projects/",
                data={
                    "name": "Repository Rollback Project",
                    "description": "Repository 생성 실패 시 프로젝트는 유지합니다.",
                    "repositoryUrl": "https://github.com/example/rollback",
                },
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(
            body["detail"]["repositoryRegistration"]["code"],
            "INTERNAL_SERVER_ERROR",
        )
        project = Project.objects.get(name="Repository Rollback Project")
        self.assertEqual(body["data"]["id"], project.pk)
        self.assertFalse(
            Repository.objects.filter(project=project).exists()
        )
        self.assertTrue(
            Member.objects.filter(
                project__name="Repository Rollback Project"
            ).exists()
        )

    def test_create_project_rejects_html_tag_input(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/v1/projects/",
            data={
                "name": "<script>alert(1)</script>",
                "description": "프로젝트 설명입니다.",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["status"], "INVALID_PROJECT_INPUT")
        self.assertEqual(
            body["detail"]["message"],
            "프로젝트명에는 HTML 태그를 입력할 수 없습니다.",
        )
        self.assertFalse(
            Project.objects.filter(name="<script>alert(1)</script>").exists()
        )

    def test_create_project_rejects_control_character_input(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/v1/projects/",
            data={
                "name": "Invalid\x01Project",
                "description": "프로젝트 설명입니다.",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["status"], "INVALID_PROJECT_INPUT")
        self.assertEqual(
            body["detail"]["message"],
            "프로젝트명에는 제어 문자를 입력할 수 없습니다.",
        )

    def test_create_project_rejects_unsupported_url_scheme(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/v1/projects/",
            data={
                "name": "Invalid URL Project",
                "description": "프로젝트 설명입니다.",
                "demoUrl": "ftp://example.com/demo",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["status"], "INVALID_PROJECT_INPUT")
        self.assertEqual(
            body["detail"]["message"],
            "URL은 http 또는 https 형식으로 입력해주세요.",
        )

    def test_project_list_first_page_pagination_order_and_count(self):
        self.create_projects_for_pagination(total=25)

        response = self.client.get("/api/v1/projects/?start=0&limit=10")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["data"]), 10)
        self.assertEqual(body["data"][0]["name"], "Project 25")
        self.assertEqual(body["data"][-1]["name"], "Project 16")
        self.assertEqual(
            body["detail"]["pagination"],
            {
                "start": 0,
                "limit": 10,
                "count": 25,
                "currentPage": 1,
                "totalPages": 3,
                "hasPrevious": False,
                "hasNext": True,
            },
        )

    def test_project_list_last_page_pagination_order_and_count(self):
        self.create_projects_for_pagination(total=25)

        response = self.client.get("/api/v1/projects/?start=20&limit=10")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body["data"]), 5)
        self.assertEqual(body["data"][0]["name"], "Project 5")
        self.assertEqual(body["data"][-1]["name"], "Project 1")
        self.assertEqual(body["detail"]["pagination"]["currentPage"], 3)
        self.assertEqual(body["detail"]["pagination"]["totalPages"], 3)
        self.assertFalse(body["detail"]["pagination"]["hasNext"])
        self.assertTrue(body["detail"]["pagination"]["hasPrevious"])

    def test_project_list_accepts_maximum_page_size(self):
        response = self.client.get("/api/v1/projects/?start=0&limit=100")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail"]["pagination"]["limit"], 100)

    def test_project_list_blank_pagination_uses_defaults(self):
        response = self.client.get("/api/v1/projects/?start=&limit=")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["detail"]["pagination"],
            {
                "start": 0,
                "limit": 12,
                "count": 1,
                "currentPage": 1,
                "totalPages": 1,
                "hasPrevious": False,
                "hasNext": False,
            },
        )

    def test_project_list_invalid_pagination_parameter(self):
        invalid_queries = (
            "start=-1&limit=10",
            "start=abc&limit=10",
            "start=0&limit=0",
            "start=0&limit=101",
        )
        for query in invalid_queries:
            with self.subTest(query=query):
                response = self.client.get(f"/api/v1/projects/?{query}")

                self.assertEqual(response.status_code, 400)
                body = response.json()
                self.assertEqual(body["status"], "INVALID_PAGINATION_PARAMETER")
                self.assertEqual(
                    body["detail"]["message"],
                    "start는 0 이상, limit은 1 이상 100 이하여야 합니다.",
                )
                self.assertEqual(body["detail"]["httpStatus"], 400)

    def project_update_payload(self, **overrides):
        payload = {
            "name": self.project.name,
            "description": self.project.description,
            "repositoryUrl": self.repository.html_url,
            "demoUrl": self.project.demo_url,
            "presentationUrl": self.project.presentation_url,
            "techStack": list(
                self.project.languages.values_list("name", flat=True)
            ),
            "status": self.project.status,
        }
        payload.update(overrides)
        return payload

    def test_project_list_owned_filter_requires_login(self):
        response = self.client.get("/api/v1/projects/?owned=true")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "PERMISSION_DENIED")

    def test_project_list_joined_filter_requires_login(self):
        response = self.client.get("/api/v1/projects/?joined=true")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "PERMISSION_DENIED")

    def test_project_list_owned_filter_returns_leader_projects_only(self):
        joined_project = Project.objects.create(
            name="Joined Project",
            description="Joined as a member",
        )
        Member.objects.create(
            project=joined_project,
            user=self.user,
            is_leader=False,
            status=Member.Status.JOINED,
        )
        self.client.force_login(self.user)

        response = self.client.get("/api/v1/projects/?owned=true")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(
            [project["id"] for project in body["data"]],
            [self.project.pk],
        )
        self.assertEqual(body["data"][0]["membershipRole"], "OWNER")
        self.assertEqual(body["detail"]["pagination"]["count"], 1)

    def test_project_list_joined_filter_excludes_leader_and_inactive_memberships(self):
        joined_project = Project.objects.create(
            name="Joined Project",
            description="Joined as a member",
        )
        Member.objects.create(
            project=joined_project,
            user=self.user,
            is_leader=False,
            status=Member.Status.JOINED,
        )
        left_project = Project.objects.create(
            name="Left Project",
            description="No longer participating",
        )
        Member.objects.create(
            project=left_project,
            user=self.user,
            is_leader=False,
            status=Member.Status.LEFT,
        )
        self.client.force_login(self.user)

        response = self.client.get("/api/v1/projects/?joined=true")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([project["id"] for project in body["data"]], [joined_project.pk])
        self.assertEqual(body["data"][0]["membershipRole"], "MEMBER")
        self.assertEqual(body["detail"]["pagination"]["count"], 1)

    def test_project_list_rejects_invalid_boolean_filter(self):
        for field in ("joined", "owned"):
            with self.subTest(field=field):
                response = self.client.get(
                    f"/api/v1/projects/?{field}=yes"
                )

                self.assertEqual(response.status_code, 400)
                body = response.json()
                self.assertEqual(body["status"], "INVALID_PROJECT_FILTER")
                self.assertEqual(
                    body["detail"]["message"],
                    f"{field}는 true 또는 false여야 합니다.",
                )
                self.assertEqual(body["detail"]["httpStatus"], 400)

    def test_project_list_accepts_numeric_boolean_filter(self):
        self.client.force_login(self.user)

        for value in ("0", "1"):
            with self.subTest(value=value):
                response = self.client.get(
                    f"/api/v1/projects/?owned={value}"
                )

                self.assertEqual(response.status_code, 200)

    def test_project_list_searches_filters_and_sorts_projects(self):
        alpha = Project.objects.create(
            name="Alpha Tools",
            description="Python helper project",
            status=Project.Status.INACTIVE,
        )
        alpha.languages.add(ProjectLanguage.objects.get(name="Go"))
        finished = Project.objects.create(
            name="Finished React",
            description="Completed frontend project",
            status=Project.Status.FINISHED,
        )
        finished.languages.add(ProjectLanguage.objects.get(name="TypeScript"))
        RepositoryLanguage.objects.create(
            repository=self.repository,
            language="TypeScript",
            bytes=200,
        )
        RepositoryLanguage.objects.create(
            repository=self.repository,
            language="Python",
            bytes=100,
        )
        RepositoryLanguage.objects.create(
            repository=self.repository,
            language="Rust",
            bytes=50,
        )

        keyword_response = self.client.get("/api/v1/projects/?keyword=python")
        stack_response = self.client.get(
            "/api/v1/projects/?techStack=TypeScript,Go&sort=name"
        )
        status_response = self.client.get("/api/v1/projects/?status=finished")
        combined_response = self.client.get(
            "/api/v1/projects/?keyword=python&techStack=Go"
        )
        repository_language_only_response = self.client.get(
            "/api/v1/projects/?techStack=Rust"
        )

        self.assertEqual(
            [project["id"] for project in keyword_response.json()["data"]],
            [alpha.pk],
        )
        self.assertEqual(
            [project["id"] for project in stack_response.json()["data"]],
            [alpha.pk, self.project.pk],
        )
        self.assertEqual(
            stack_response.json()["data"][1]["repository"]["languages"],
            ["TypeScript", "Python", "Rust"],
        )
        self.assertEqual(
            [project["id"] for project in status_response.json()["data"]],
            [finished.pk],
        )
        self.assertEqual(
            [project["id"] for project in combined_response.json()["data"]],
            [alpha.pk],
        )
        self.assertEqual(repository_language_only_response.json()["data"], [])

    def test_project_list_rejects_invalid_search_filter(self):
        for query in (
            "status=DELETED",
            "sort=popular",
            f"keyword={'x' * 101}",
            f"techStack={'x' * 51}",
        ):
            with self.subTest(query=query):
                response = self.client.get(f"/api/v1/projects/?{query}")

                self.assertEqual(response.status_code, 400)
                self.assertEqual(
                    response.json()["status"],
                    "INVALID_PROJECT_FILTER",
                )

    def test_project_membership_history_requires_login(self):
        response = self.client.get("/api/v1/projects/members")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "PERMISSION_DENIED")

    def test_login_required_project_endpoints_keep_error_contract(self):
        responses = (
            self.client.post("/api/v1/projects/"),
            self.client.get("/api/v1/projects/members"),
            self.client.get(f"/api/v1/projects/{self.project.pk}/members"),
            self.client.post(f"/api/v1/projects/{self.project.pk}/members"),
            self.client.delete(f"/api/v1/projects/{self.project.pk}/members"),
            self.client.put(
                f"/api/v1/projects/{self.project.pk}/members/{self.member.pk}",
                data={"status": Member.Status.JOINED},
                content_type="application/json",
            ),
        )

        for response in responses:
            with self.subTest(path=response.request["PATH_INFO"]):
                self.assertEqual(response.status_code, 403)
                self.assertEqual(response.json()["status"], "PERMISSION_DENIED")
                self.assertEqual(
                    response.json()["detail"],
                    {
                        "message": "로그인이 필요합니다.",
                        "httpStatus": 403,
                    },
                )

    def test_project_membership_application_creates_pending_history(self):
        applicant = get_user_model().objects.create_user(
            username="applicant",
            password="password",
            github_email="applicant@sookmyung.ac.kr",
            name="신청자",
            student_id=222,
            major="컴퓨터과학",
        )
        self.client.force_login(applicant)

        response = self.client.post(f"/api/v1/projects/{self.project.pk}/members")

        self.assertEqual(response.status_code, 201)
        membership = Member.objects.get(
            project=self.project,
            user=applicant,
            is_leader=False,
        )
        self.assertEqual(membership.status, Member.Status.PENDING)
        self.assertIsNone(response.json()["data"])

    def test_project_membership_application_rejects_active_membership(self):
        applicant = get_user_model().objects.create_user(
            username="active-applicant",
            password="password",
            github_email="active-applicant@sookmyung.ac.kr",
            name="신청중 사용자",
            student_id=223,
            major="컴퓨터과학",
        )
        Member.objects.create(
            project=self.project,
            user=applicant,
            status=Member.Status.PENDING,
        )
        self.client.force_login(applicant)

        response = self.client.post(f"/api/v1/projects/{self.project.pk}/members")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "MEMBERSHIP_ALREADY_EXISTS")
        self.assertEqual(
            Member.objects.filter(project=self.project, user=applicant).count(),
            1,
        )

    def test_project_membership_application_rejects_full_project(self):
        applicant = get_user_model().objects.create_user(
            username="capacity-applicant",
            password="password",
            github_email="capacity-applicant@sookmyung.ac.kr",
            name="정원 초과 신청자",
            student_id=225,
            major="컴퓨터과학",
        )
        for _ in range(self.project.max_members - 1):
            Member.objects.create(
                project=self.project,
                status=Member.Status.JOINED,
            )
        self.client.force_login(applicant)

        application_response = self.client.post(
            f"/api/v1/projects/{self.project.pk}/members"
        )

        self.assertEqual(application_response.status_code, 400)
        self.assertEqual(
            application_response.json()["status"],
            "PROJECT_CAPACITY_REACHED",
        )
        self.assertFalse(
            Member.objects.filter(project=self.project, user=applicant).exists()
        )

    def test_project_leader_cannot_apply_to_own_project(self):
        self.client.force_login(self.user)

        response = self.client.post(f"/api/v1/projects/{self.project.pk}/members")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "MEMBERSHIP_ALREADY_EXISTS")
        self.assertEqual(
            Member.objects.filter(project=self.project, user=self.user).count(),
            1,
        )

    def test_project_membership_application_allows_five_reapplications(self):
        applicant = get_user_model().objects.create_user(
            username="returning-applicant",
            password="password",
            github_email="returning-applicant@sookmyung.ac.kr",
            name="재신청자",
            student_id=224,
            major="컴퓨터과학",
        )
        for status_value in (
            Member.Status.DECLINED,
            Member.Status.CANCELED,
            Member.Status.LEFT,
            Member.Status.DECLINED,
            Member.Status.CANCELED,
        ):
            Member.objects.create(
                project=self.project,
                user=applicant,
                status=status_value,
            )
        self.client.force_login(applicant)

        response = self.client.post(f"/api/v1/projects/{self.project.pk}/members")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            Member.objects.filter(project=self.project, user=applicant).count(),
            6,
        )
        Member.objects.filter(
            project=self.project,
            user=applicant,
            status=Member.Status.PENDING,
        ).update(status=Member.Status.DECLINED)

        response = self.client.post(f"/api/v1/projects/{self.project.pk}/members")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["status"], "MEMBERSHIP_REAPPLICATION_LIMIT"
        )
        self.assertEqual(
            response.json()["detail"]["message"],
            "현재 참가 신청할 수 없습니다.",
        )

    def test_project_membership_application_rejects_invalid_project(self):
        self.client.force_login(self.user)

        missing_response = self.client.post("/api/v1/projects/999999/members")
        self.project.status = Project.Status.FINISHED
        self.project.save(update_fields=("status", "updated_at"))
        inactive_response = self.client.post(
            f"/api/v1/projects/{self.project.pk}/members"
        )

        self.assertEqual(missing_response.status_code, 404)
        self.assertEqual(inactive_response.status_code, 400)
        self.assertEqual(
            inactive_response.json()["status"], "INVALID_PROJECT_STATUS"
        )

    def test_project_membership_application_requires_login(self):
        response = self.client.post(f"/api/v1/projects/{self.project.pk}/members")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "PERMISSION_DENIED")

    def test_project_membership_history_returns_all_attempts_latest_first(self):
        application_project = Project.objects.create(
            name="Application Project",
            description="Application history target",
        )
        declined = Member.objects.create(
            project=application_project,
            user=self.user,
            status=Member.Status.DECLINED,
            description="모집 인원 마감",
        )
        pending = Member.objects.create(
            project=application_project,
            user=self.user,
            status=Member.Status.PENDING,
        )
        other_user = get_user_model().objects.create_user(
            username="other-applicant",
            password="password",
            github_email="other-applicant@sookmyung.ac.kr",
            name="다른 신청자",
            student_id=220,
            major="컴퓨터과학",
        )
        Member.objects.create(
            project=application_project,
            user=other_user,
            status=Member.Status.PENDING,
        )
        older_time = timezone.now() - timedelta(days=1)
        Member.objects.filter(pk=declined.pk).update(created_at=older_time)
        self.client.force_login(self.user)

        response = self.client.get("/api/v1/projects/members")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(body["detail"]["pagination"]["count"], 2)
        self.assertEqual(body["detail"]["pagination"]["limit"], 12)
        self.assertEqual(
            [membership["id"] for membership in body["data"]],
            [pending.pk, declined.pk],
        )
        self.assertEqual(
            [membership["status"] for membership in body["data"]],
            [Member.Status.PENDING, Member.Status.DECLINED],
        )
        self.assertEqual(body["data"][0]["projectId"], application_project.pk)
        self.assertEqual(body["data"][0]["projectName"], "Application Project")
        self.assertEqual(body["data"][0]["projectStatus"], Project.Status.ACTIVE)
        self.assertNotIn("userId", body["data"][0])
        self.assertNotIn("joinedAt", body["data"][0])
        self.assertIn("createdAt", body["data"][0])
        self.assertIn("updatedAt", body["data"][0])

        filtered = self.client.get(
            "/api/v1/projects/members"
            "?start=0&limit=1&status=PENDING,DECLINED&sort=oldest"
        )
        self.assertEqual(filtered.status_code, 200)
        self.assertEqual(filtered.json()["data"][0]["id"], declined.pk)
        self.assertEqual(
            filtered.json()["detail"]["pagination"]["count"],
            2,
        )

    def test_project_membership_history_rejects_invalid_query(self):
        self.client.force_login(self.user)

        cases = (
            ("start=-1", "INVALID_PAGINATION_PARAMETER"),
            ("limit=0", "INVALID_PAGINATION_PARAMETER"),
            ("limit=101", "INVALID_PAGINATION_PARAMETER"),
            ("status=UNKNOWN", "INVALID_MEMBER_FILTER"),
            ("sort=popular", "INVALID_MEMBER_FILTER"),
        )
        for query, expected_status in cases:
            with self.subTest(query=query):
                response = self.client.get(f"/api/v1/projects/members?{query}")

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["status"], expected_status)

    def test_project_membership_history_returns_empty_list(self):
        self.client.force_login(self.user)

        response = self.client.get("/api/v1/projects/members")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [])

    def test_project_membership_history_hides_deleted_projects(self):
        self.project.status = Project.Status.DELETED
        self.project.save(update_fields=("status", "updated_at"))
        self.member.is_leader = False
        self.member.save(update_fields=("is_leader", "updated_at"))
        self.client.force_login(self.user)

        response = self.client.get("/api/v1/projects/members")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"], [])

    def test_member_transition_to_changes_status_without_saving(self):
        membership = Member.objects.create(
            project=self.project,
            user=self.user,
            status=Member.Status.PENDING,
        )

        membership.transition_to(Member.Status.CANCELED)

        self.assertEqual(membership.status, Member.Status.CANCELED)
        membership.refresh_from_db()
        self.assertEqual(membership.status, Member.Status.PENDING)

    def test_member_transition_to_rejects_invalid_status(self):
        membership = Member.objects.create(
            project=self.project,
            user=self.user,
            status=Member.Status.DECLINED,
        )

        with self.assertRaises(ValidationError):
            membership.transition_to(Member.Status.LEFT)

    def test_member_transition_to_requires_reason_when_requested(self):
        membership = Member.objects.create(
            project=self.project,
            user=self.user,
            status=Member.Status.JOINED,
        )

        with self.assertRaisesMessage(
            ValidationError,
            "멤버를 내보내려면 사유를 입력해주세요.",
        ):
            membership.transition_to(
                Member.Status.LEFT,
                require_description=True,
            )

        self.assertEqual(membership.status, Member.Status.JOINED)

    def test_pending_project_membership_can_be_canceled(self):
        application_project = Project.objects.create(
            name="Pending Application Project",
            description="Pending application project description",
        )
        pending_member = Member.objects.create(
            project=application_project,
            user=self.user,
            status=Member.Status.PENDING,
        )
        self.client.force_login(self.user)

        response = self.client.delete(
            f"/api/v1/projects/{application_project.pk}/members"
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "SUCCESS")
        self.assertIsNone(response.json()["data"])
        pending_member.refresh_from_db()
        self.assertEqual(pending_member.status, Member.Status.CANCELED)

    def test_joined_project_membership_can_be_left(self):
        joined_project = Project.objects.create(
            name="Joined Project",
            description="Joined project description",
        )
        joined_member = Member.objects.create(
            project=joined_project,
            user=self.user,
            status=Member.Status.JOINED,
        )
        self.client.force_login(self.user)

        response = self.client.delete(
            f"/api/v1/projects/{joined_project.pk}/members",
            data={"description": "개인 일정으로 탈퇴"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        joined_member.refresh_from_db()
        self.assertEqual(joined_member.status, Member.Status.LEFT)
        self.assertEqual(joined_member.description, "개인 일정으로 탈퇴")

    def test_project_leader_cannot_leave(self):
        self.client.force_login(self.user)

        response = self.client.delete(f"/api/v1/projects/{self.project.pk}/members")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "PERMISSION_DENIED")
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, Member.Status.JOINED)

    def test_project_leader_cannot_cancel_later_pending_membership(self):
        pending_member = Member.objects.create(
            project=self.project,
            user=self.user,
            status=Member.Status.PENDING,
        )
        self.client.force_login(self.user)

        response = self.client.delete(f"/api/v1/projects/{self.project.pk}/members")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "PERMISSION_DENIED")
        pending_member.refresh_from_db()
        self.assertEqual(pending_member.status, Member.Status.PENDING)

    def test_project_membership_cancel_rejects_inactive_status(self):
        declined_project = Project.objects.create(
            name="Declined Application Project",
            description="Declined application project description",
        )
        declined_member = Member.objects.create(
            project=declined_project,
            user=self.user,
            status=Member.Status.DECLINED,
        )
        self.client.force_login(self.user)

        response = self.client.delete(
            f"/api/v1/projects/{declined_project.pk}/members"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "INVALID_MEMBER_STATUS")
        declined_member.refresh_from_db()
        self.assertEqual(declined_member.status, Member.Status.DECLINED)

    def test_project_membership_cancel_requires_login(self):
        response = self.client.delete(f"/api/v1/projects/{self.project.pk}/members")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "PERMISSION_DENIED")

    def test_project_membership_cancel_rejects_user_without_membership(self):
        other_user = get_user_model().objects.create_user(
            username="non-member",
            password="password",
            github_email="non-member@sookmyung.ac.kr",
            name="비회원",
            student_id=221,
            major="컴퓨터과학",
        )
        self.client.force_login(other_user)

        response = self.client.delete(f"/api/v1/projects/{self.project.pk}/members")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["status"], "MEMBERSHIP_NOT_FOUND")

    def test_project_members_can_list_joined_members_and_leader_can_manage(self):
        joined_user = get_user_model().objects.create_user(
            username="joined-user",
            password="password",
            github_email="joined-user@sookmyung.ac.kr",
            name="참여자",
            student_id=230,
            major="컴퓨터과학",
        )
        pending_user = get_user_model().objects.create_user(
            username="pending-user",
            password="password",
            github_email="pending-user@sookmyung.ac.kr",
            name="신청자",
            student_id=231,
            major="컴퓨터과학",
        )
        joined = Member.objects.create(
            project=self.project,
            user=joined_user,
            status=Member.Status.JOINED,
        )
        pending = Member.objects.create(
            project=self.project,
            user=pending_user,
            status=Member.Status.PENDING,
        )

        self.client.force_login(joined_user)
        response = self.client.get(f"/api/v1/projects/{self.project.pk}/members")
        denied = self.client.get(
            f"/api/v1/projects/{self.project.pk}/members?manage=true"
        )
        update_denied = self.client.put(
            f"/api/v1/projects/{self.project.pk}/members/{pending.pk}",
            data={"status": Member.Status.JOINED},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {member["id"] for member in response.json()["data"]},
            {self.member.pk, joined.pk},
        )
        member = response.json()["data"][0]
        self.assertIn("username", member)
        self.assertIn("role", member)
        self.assertIn("joinedAt", member)
        self.assertNotIn("userId", member)
        self.assertNotIn("status", member)
        self.assertNotIn("description", member)
        self.assertNotIn("createdAt", member)
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(update_denied.status_code, 403)
        self.assertEqual(
            update_denied.json()["detail"]["message"],
            "프로젝트 접근 권한이 없습니다.",
        )

        self.client.force_login(self.user)
        managed = self.client.get(
            f"/api/v1/projects/{self.project.pk}/members?manage=true"
        )

        self.assertEqual(managed.status_code, 200)
        managed_members = {
            member["id"]: member for member in managed.json()["data"]
        }
        self.assertEqual(managed_members[joined.pk]["name"], "참여자")
        self.assertIn(pending.pk, managed_members)
        self.assertIn("description", managed_members[pending.pk])
        self.assertIsNone(managed_members[pending.pk]["description"])
        self.assertIn("createdAt", managed_members[pending.pk])
        self.assertNotIn("username", managed_members[pending.pk])
        self.assertNotIn("role", managed_members[pending.pk])
        self.assertNotIn("joinedAt", managed_members[pending.pk])

        pending_only = self.client.get(
            f"/api/v1/projects/{self.project.pk}/members"
            "?manage=true&status=PENDING"
        )
        self.assertEqual(pending_only.status_code, 200)
        self.assertEqual(
            [member["id"] for member in pending_only.json()["data"]],
            [pending.pk],
        )

    def test_project_members_reject_invalid_manage_filter(self):
        self.client.force_login(self.user)

        response = self.client.get(
            f"/api/v1/projects/{self.project.pk}/members?manage=yes"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "INVALID_MEMBER_FILTER")
        self.assertEqual(
            response.json()["detail"]["message"],
            "manage는 true 또는 false여야 합니다.",
        )

    def test_project_members_reject_status_filter_without_manage(self):
        self.client.force_login(self.user)

        response = self.client.get(
            f"/api/v1/projects/{self.project.pk}/members?status=PENDING"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "INVALID_MEMBER_FILTER")
        self.assertEqual(
            response.json()["detail"]["message"],
            (
                "status는 유효한 멤버 상태이며 manage=true일 때만 "
                "사용할 수 있습니다."
            ),
        )

    def test_project_members_reject_unknown_status_filter(self):
        self.client.force_login(self.user)

        response = self.client.get(
            f"/api/v1/projects/{self.project.pk}/members"
            "?manage=true&status=UNKNOWN"
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "INVALID_MEMBER_FILTER")

    def test_non_member_cannot_list_project_members(self):
        outsider = get_user_model().objects.create_user(
            username="outsider",
            password="password",
            github_email="outsider@sookmyung.ac.kr",
            name="외부인",
            student_id=232,
            major="컴퓨터과학",
        )
        self.client.force_login(outsider)

        response = self.client.get(f"/api/v1/projects/{self.project.pk}/members")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "PERMISSION_DENIED")
        self.assertEqual(
            response.json()["detail"]["message"],
            "프로젝트 접근 권한이 없습니다.",
        )

    def test_project_leader_can_apply_confirmed_member_transitions(self):
        applicant = get_user_model().objects.create_user(
            username="managed-applicant",
            password="password",
            github_email="managed-applicant@sookmyung.ac.kr",
            name="관리 대상",
            student_id=233,
            major="컴퓨터과학",
        )
        pending = Member.objects.create(
            project=self.project,
            user=applicant,
            status=Member.Status.PENDING,
        )
        pending_to_decline = Member.objects.create(
            project=self.project,
            user=applicant,
            status=Member.Status.PENDING,
        )
        joined = Member.objects.create(
            project=self.project,
            user=applicant,
            status=Member.Status.JOINED,
        )
        joined_without_reason = Member.objects.create(
            project=self.project,
            user=applicant,
            status=Member.Status.JOINED,
        )
        self.client.force_login(self.user)

        approved = self.client.put(
            f"/api/v1/projects/{self.project.pk}/members/{pending.pk}",
            data={"status": Member.Status.JOINED},
            content_type="application/json",
        )
        declined = self.client.put(
            f"/api/v1/projects/{self.project.pk}/members/{pending_to_decline.pk}",
            data={
                "status": Member.Status.DECLINED,
                "description": "모집 역할 불일치",
            },
            content_type="application/json",
        )
        left = self.client.put(
            f"/api/v1/projects/{self.project.pk}/members/{joined.pk}",
            data={"status": Member.Status.LEFT, "description": "프로젝트 종료"},
            content_type="application/json",
        )
        missing_reason = self.client.put(
            f"/api/v1/projects/{self.project.pk}/members/{joined_without_reason.pk}",
            data={"status": Member.Status.LEFT},
            content_type="application/json",
        )

        self.assertEqual(approved.status_code, 200)
        self.assertIsNone(approved.json()["data"])
        self.assertEqual(declined.status_code, 200)
        self.assertIsNone(declined.json()["data"])
        self.assertEqual(left.status_code, 200)
        self.assertIsNone(left.json()["data"])
        self.assertEqual(missing_reason.status_code, 400)
        self.assertEqual(
            missing_reason.json()["status"],
            "INVALID_MEMBER_INPUT",
        )
        pending.refresh_from_db()
        pending_to_decline.refresh_from_db()
        joined.refresh_from_db()
        joined_without_reason.refresh_from_db()
        self.assertEqual(pending.status, Member.Status.JOINED)
        self.assertIsNotNone(pending.joined_at)
        self.assertIsNone(pending.description)
        self.assertEqual(pending_to_decline.status, Member.Status.DECLINED)
        self.assertEqual(pending_to_decline.description, "모집 역할 불일치")
        self.assertEqual(joined.status, Member.Status.LEFT)
        self.assertEqual(joined.description, "프로젝트 종료")
        self.assertEqual(joined_without_reason.status, Member.Status.JOINED)

    def test_project_member_approval_rejects_full_project(self):
        applicant = get_user_model().objects.create_user(
            username="capacity-managed-applicant",
            password="password",
            github_email="capacity-managed-applicant@sookmyung.ac.kr",
            name="정원 초과 승인 대상",
            student_id=235,
            major="컴퓨터과학",
        )
        pending = Member.objects.create(
            project=self.project,
            user=applicant,
            status=Member.Status.PENDING,
        )
        for _ in range(self.project.max_members - 1):
            Member.objects.create(
                project=self.project,
                status=Member.Status.JOINED,
            )
        self.client.force_login(self.user)

        response = self.client.put(
            f"/api/v1/projects/{self.project.pk}/members/{pending.pk}",
            data={"status": Member.Status.JOINED},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "PROJECT_CAPACITY_REACHED")
        pending.refresh_from_db()
        self.assertEqual(pending.status, Member.Status.PENDING)
        self.assertIsNone(pending.joined_at)

    def test_project_member_update_rejects_invalid_transition_and_target(self):
        applicant = get_user_model().objects.create_user(
            username="declined-applicant",
            password="password",
            github_email="declined-applicant@sookmyung.ac.kr",
            name="반려 대상",
            student_id=234,
            major="컴퓨터과학",
        )
        declined = Member.objects.create(
            project=self.project,
            user=applicant,
            status=Member.Status.DECLINED,
        )
        other_project = Project.objects.create(
            name="Other Project",
            description="다른 프로젝트",
        )
        other_member = Member.objects.create(
            project=other_project,
            user=applicant,
            status=Member.Status.PENDING,
        )
        self.client.force_login(self.user)

        invalid = self.client.put(
            f"/api/v1/projects/{self.project.pk}/members/{declined.pk}",
            data={"status": Member.Status.JOINED},
            content_type="application/json",
        )
        missing = self.client.put(
            f"/api/v1/projects/{self.project.pk}/members/{other_member.pk}",
            data={"status": Member.Status.JOINED},
            content_type="application/json",
        )
        leader = self.client.put(
            f"/api/v1/projects/{self.project.pk}/members/{self.member.pk}",
            data={
                "status": Member.Status.LEFT,
                "description": "팀장 내보내기 시도",
            },
            content_type="application/json",
        )

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()["status"], "INVALID_MEMBER_STATUS")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["status"], "MEMBER_NOT_FOUND")
        self.assertEqual(leader.status_code, 404)
        self.assertEqual(leader.json()["status"], "MEMBER_NOT_FOUND")

    def create_projects_for_pagination(self, total):
        self.project.delete()
        base = timezone.now()
        created_projects = []
        language = ProjectLanguage.objects.get(name="TypeScript")

        for index in range(1, total + 1):
            project = Project.objects.create(
                name=f"Project {index}",
                description=f"Project {index} description",
                status=Project.Status.ACTIVE,
            )
            project.languages.add(language)
            created_projects.append(project)

        for index, project in enumerate(created_projects, start=1):
            Project.objects.filter(pk=project.pk).update(
                updated_at=base + timedelta(minutes=index)
            )
