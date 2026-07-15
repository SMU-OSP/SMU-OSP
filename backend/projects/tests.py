from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import Project, Repository


class ProjectApiTests(TestCase):
    def setUp(self):
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
