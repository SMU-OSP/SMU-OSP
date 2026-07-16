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
                "repositoryUrl": "",
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

    @patch("projects.views.upsert_repository_from_url")
    def test_create_project_rejects_duplicate_repository(self, mock_upsert):
        self.client.force_login(self.user)
        mock_upsert.return_value = self.project.repository

        response = self.client.post(
            "/api/v1/projects/",
            data={
                "name": "Repository Duplicate Project",
                "description": "다른 프로젝트명으로 같은 Repository를 등록합니다.",
                "repositoryUrl": "https://github.com/Jiyeon125/SMU-OSP",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["status"], "DUPLICATE_PROJECT_REPOSITORY")
        self.assertEqual(
            body["detail"]["message"],
            "이미 다른 프로젝트에 연결된 Repository입니다.",
        )
        self.assertFalse(
            Project.objects.filter(name="Repository Duplicate Project").exists()
        )

    def test_project_list_filters_and_sorts_on_backend(self):
        self.create_project_with_repository(
            name="Alpha Project",
            tech_stack=["FastAPI"],
            language="Python",
            stars=8,
            visibility=Project.Visibility.PUBLIC,
            github_id=201,
        )
        self.create_project_with_repository(
            name="Beta Project",
            tech_stack=["Spring"],
            language="Java",
            stars=15,
            visibility=Project.Visibility.PRIVATE,
            github_id=202,
        )

        keyword_response = self.client.get("/api/v1/projects/?keyword=Alpha")
        keyword_body = keyword_response.json()
        self.assertEqual(keyword_response.status_code, 200)
        self.assertEqual([p["name"] for p in keyword_body["data"]], ["Alpha Project"])

        stack_response = self.client.get("/api/v1/projects/?techStack=FastAPI")
        stack_body = stack_response.json()
        self.assertEqual(stack_response.status_code, 200)
        self.assertEqual([p["name"] for p in stack_body["data"]], ["Alpha Project"])

        visibility_response = self.client.get("/api/v1/projects/?visibility=PRIVATE")
        visibility_body = visibility_response.json()
        self.assertEqual(visibility_response.status_code, 200)
        self.assertEqual(
            [p["name"] for p in visibility_body["data"]],
            ["Beta Project"],
        )

        sort_response = self.client.get("/api/v1/projects/?sort=stars&limit=3")
        sort_body = sort_response.json()
        self.assertEqual(sort_response.status_code, 200)
        self.assertEqual(sort_body["data"][0]["name"], "Beta Project")

    def test_project_list_invalid_filter_parameter(self):
        response = self.client.get("/api/v1/projects/?visibility=INVALID")

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["status"], "INVALID_PROJECT_FILTER")
        self.assertEqual(body["detail"]["httpStatus"], 400)

    def test_project_filter_options(self):
        self.create_project_with_repository(
            name="Filter Option Project",
            tech_stack=["FastAPI", "React"],
            language="Python",
            stars=1,
            visibility=Project.Visibility.PUBLIC,
            github_id=203,
        )

        response = self.client.get("/api/v1/projects/options")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertIn("React", body["data"]["techStacks"])
        self.assertIn("FastAPI", body["data"]["techStacks"])
        self.assertIn("Python", body["data"]["languages"])

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

    def create_project_with_repository(
        self,
        name,
        tech_stack,
        language,
        stars,
        visibility,
        github_id,
    ):
        team = Team.objects.create(
            name=name,
            description=f"{name} description",
        )
        repository = Repository.objects.create(
            github_id=github_id,
            name=name.lower().replace(" ", "-"),
            full_name=f"example/{name.lower().replace(' ', '-')}",
            description=f"{name} repository",
            stars=stars,
            forks=0,
            language=language,
            topics=[],
            html_url=f"https://github.com/example/{name.lower().replace(' ', '-')}",
            github_updated_at=timezone.now(),
            fetched_at=timezone.now(),
            refresh_status=Repository.RefreshStatus.SUCCESS,
        )
        return Project.objects.create(
            team=team,
            name=name,
            description=f"{name} description",
            repository=repository,
            repository_url=repository.html_url,
            tech_stack=tech_stack,
            used_open_source=[],
            visibility=visibility,
        )
