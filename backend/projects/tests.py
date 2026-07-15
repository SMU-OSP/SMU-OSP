from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from teams.models import Team

from .models import Project, Repository


class ProjectApiTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="Jiyeon125",
            password="password",
            github_email="0215wldus@gmail.com",
            name="권지연",
            student_id=2413640,
            major="데이터사이언스전공",
        )
        self.team = Team.objects.create(
            name="SOSP Team",
            leader=self.user,
            leader_name="권지연",
        )
        repository = Repository.objects.create(
            github_id=101,
            name="SMU-OSP",
            full_name="Jiyeon125/SMU-OSP",
            description="SMU Open-Source Platform",
            stars=0,
            forks=0,
            language="TypeScript",
            topics=["django", "react"],
            html_url="https://github.com/Jiyeon125/SMU-OSP",
            github_updated_at=timezone.now(),
            fetched_at=timezone.now(),
            refresh_status=Repository.RefreshStatus.SUCCESS,
        )
        self.project = Project.objects.create(
            team_id=1,
            team_name="SOSP Team",
            name="SOSP",
            description="SMU Open-Source Platform",
            repository=repository,
            repository_url="https://github.com/Jiyeon125/SMU-OSP",
            demo_url="https://sosp.sookmyung.ac.kr",
            tech_stack=["React", "Django"],
            used_open_source=["Django REST framework"],
            visibility=Project.Visibility.PUBLIC,
        )

    def test_project_list_response_shape(self):
        response = self.client.get("/api/v1/projects/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(len(body["data"]), 1)
        self.assertEqual(body["data"][0]["name"], "SOSP")
        self.assertEqual(body["data"][0]["teamName"], "SOSP Team")
        self.assertEqual(body["data"][0]["repository"]["fullName"], "Jiyeon125/SMU-OSP")
        self.assertEqual(body["detail"]["pagination"]["count"], 1)
        self.assertEqual(body["detail"]["pagination"]["currentPage"], 1)

    def test_project_detail_response_shape(self):
        response = self.client.get(f"/api/v1/projects/{self.project.pk}")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(body["data"]["id"], self.project.pk)
        self.assertEqual(body["data"]["repositoryUrl"], "https://github.com/Jiyeon125/SMU-OSP")

    def test_project_detail_not_found(self):
        response = self.client.get("/api/v1/projects/999")

        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertEqual(body["status"], "PROJECT_NOT_FOUND")
        self.assertIsNone(body["data"])
        self.assertEqual(body["detail"]["httpStatus"], 404)

    def test_project_delete_removes_repository(self):
        repository_id = self.project.repository_id

        Project.objects.filter(pk=self.project.pk).delete()

        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())
        self.assertFalse(Repository.objects.filter(pk=repository_id).exists())

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

    def test_project_list_invalid_pagination_parameter(self):
        response = self.client.get("/api/v1/projects/?start=-1&limit=10")

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["status"], "INVALID_PAGINATION_PARAMETER")
        self.assertEqual(body["detail"]["httpStatus"], 400)

    def test_create_project_requires_login(self):
        response = self.client.post(
            "/api/v1/projects/",
            self.project_payload(),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 403)
        body = response.json()
        self.assertEqual(body["status"], "PERMISSION_DENIED")

    def test_create_project_requires_existing_team(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/v1/projects/",
            self.project_payload(teamId=999),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertEqual(body["status"], "TEAM_NOT_FOUND")

    def test_create_project_with_required_fields(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/v1/projects/",
            self.project_payload(),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(body["data"]["teamId"], self.team.pk)
        self.assertEqual(body["data"]["teamName"], "SOSP Team")
        self.assertEqual(body["data"]["name"], "New Project")
        self.assertIsNone(body["data"]["repository"])

    def test_create_project_reuses_idempotency_key(self):
        self.client.force_login(self.user)
        payload = self.project_payload(idempotencyKey="project-once")

        first_response = self.client.post(
            "/api/v1/projects/",
            payload,
            content_type="application/json",
        )
        second_response = self.client.post(
            "/api/v1/projects/",
            payload,
            content_type="application/json",
        )

        self.assertEqual(first_response.status_code, 201)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(
            first_response.json()["data"]["id"],
            second_response.json()["data"]["id"],
        )
        self.assertEqual(
            Project.objects.filter(idempotency_key="project-once").count(),
            1,
        )

    @patch("projects.views.upsert_repository_from_url")
    def test_create_project_links_repository_when_repository_url_exists(self, mock_upsert):
        self.client.force_login(self.user)
        repository = Repository.objects.create(
            github_id=202,
            name="new-project",
            full_name="example/new-project",
            description="New Project",
            stars=3,
            forks=1,
            language="Python",
            topics=["django"],
            html_url="https://github.com/example/new-project",
            github_updated_at=timezone.now(),
            fetched_at=timezone.now(),
            refresh_status=Repository.RefreshStatus.SUCCESS,
        )
        mock_upsert.return_value = repository

        response = self.client.post(
            "/api/v1/projects/",
            self.project_payload(
                idempotencyKey="project-with-repo",
                repositoryUrl="https://github.com/example/new-project",
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(body["data"]["repository"]["fullName"], "example/new-project")
        mock_upsert.assert_called_once_with("https://github.com/example/new-project")

    def test_create_project_rejects_invalid_repository_url(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/v1/projects/",
            self.project_payload(repositoryUrl="https://example.com/not-github"),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["status"], "INVALID_GITHUB_URL")

    def create_projects_for_pagination(self, total):
        self.project.delete()
        base = timezone.now()
        created_projects = []

        for index in range(1, total + 1):
            project = Project.objects.create(
                team_id=1,
                team_name="SOSP Team",
                name=f"Project {index}",
                description=f"Project {index} description",
                repository_url=f"https://github.com/example/project-{index}",
                tech_stack=["React"],
                used_open_source=["Django REST framework"],
                visibility=Project.Visibility.PUBLIC,
            )
            created_projects.append(project)

        for index, project in enumerate(created_projects, start=1):
            Project.objects.filter(pk=project.pk).update(
                updated_at=base + timedelta(minutes=index)
            )

    def project_payload(self, **overrides):
        payload = {
            "idempotencyKey": "project-create-1",
            "teamId": self.team.pk,
            "name": "New Project",
            "description": "New Project Description",
            "repositoryUrl": "",
            "demoUrl": "",
            "presentationUrl": "",
            "techStack": ["Django", "React"],
            "usedOpenSource": ["Django REST framework"],
            "visibility": Project.Visibility.PUBLIC,
        }
        payload.update(overrides)
        return payload
