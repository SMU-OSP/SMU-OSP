from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from teams.models import Team

from .models import Project, Repository


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
        self.team = Team.objects.create(
            name="SOSP",
            description="SMU Open-Source Platform",
            leader=self.user,
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
            team=self.team,
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
        self.assertNotIn("teamName", body["data"][0])
        self.assertNotIn("teamId", body["data"][0])
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
        team_id = self.project.team_id

        Project.objects.filter(pk=self.project.pk).delete()

        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())
        self.assertFalse(Repository.objects.filter(pk=repository_id).exists())
        self.assertFalse(Team.objects.filter(pk=team_id).exists())

    def test_create_project_creates_internal_team(self):
        self.client.force_login(self.user)

        response = self.client.post(
            "/api/v1/projects/",
            data={
                "name": "New Project",
                "description": "프로젝트 정보만 입력해 등록합니다.",
                "repositoryUrl": "https://github.com/example/new-project",
                "demoUrl": "",
                "presentationUrl": "",
                "techStack": ["React", "Django"],
                "usedOpenSource": ["Django REST framework"],
                "visibility": "PUBLIC",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(body["data"]["name"], "New Project")
        self.assertNotIn("teamName", body["data"])
        self.assertTrue(Team.objects.filter(name="New Project").exists())
        created_project = Project.objects.get(name="New Project")
        self.assertEqual(created_project.team.name, "New Project")
        self.assertEqual(created_project.team.leader_name, self.user.name)
        self.assertEqual(
            created_project.repository_url,
            "https://github.com/example/new-project",
        )
        self.assertIsNone(created_project.repository_id)

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
            team = Team.objects.create(
                name=f"Project {index}",
                description=f"Project {index} description",
            )
            project = Project.objects.create(
                team=team,
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
