from django.test import TestCase
from django.urls import reverse
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
        self.assertIsNone(body["detail"])
        self.assertEqual(len(body["data"]), 1)
        self.assertEqual(body["data"][0]["name"], "SOSP")
        self.assertEqual(body["data"][0]["teamName"], "SOSP Team")
        self.assertEqual(body["data"][0]["repository"]["fullName"], "Jiyeon125/SMU-OSP")

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
