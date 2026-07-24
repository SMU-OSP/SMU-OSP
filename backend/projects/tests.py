from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection
from django.test import TestCase, override_settings
from django.utils import timezone

from .models import Member, Project, Repository


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
            tech_stack=["React", "Django"],
            used_open_source=["Django REST framework"],
            status=Project.Status.ACTIVE,
        )
        self.repository = Repository.objects.create(
            project=self.project,
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
        self.assertEqual(body["data"][0]["status"], "ACTIVE")
        self.assertEqual(body["data"][0]["maxMembers"], 5)
        self.assertIsNone(body["data"][0]["membershipRole"])
        self.assertEqual(body["data"][0]["repository"]["fullName"], "Jiyeon125/SMU-OSP")
        self.assertEqual(body["detail"]["pagination"]["count"], 1)
        self.assertEqual(body["detail"]["pagination"]["currentPage"], 1)

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
        self.assertNotIn("canApply", body["data"])
        self.assertNotIn("applicationStatus", body["data"])
        self.assertIsNone(body["data"]["members"])

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
        self.assertEqual(data["members"][1]["description"], "프론트엔드")

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

    def test_project_leader_can_update_all_project_fields(self):
        repository_id = self.repository.pk
        self.client.force_login(self.user)

        response = self.client.put(
            f"/api/v1/projects/{self.project.pk}",
            data=self.project_update_payload(
                name="Updated SOSP",
                description="수정된 프로젝트 설명",
                repositoryUrl="https://github.com/example/updated-project",
                demoUrl="https://updated.example.com",
                presentationUrl="https://updated.example.com/slides",
                techStack=["React", "Django", "MySQL"],
                usedOpenSource=["Django REST framework", "Chakra UI"],
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
        self.assertEqual(self.project.tech_stack, ["React", "Django", "MySQL"])
        self.assertEqual(
            self.project.used_open_source,
            ["Django REST framework", "Chakra UI"],
        )

        repository = Repository.objects.get(pk=repository_id)
        self.assertEqual(
            repository.html_url,
            "https://github.com/example/updated-project",
        )
        self.assertIsNone(repository.github_id)
        self.assertIsNone(repository.description)
        self.assertEqual(repository.stars, 0)
        self.assertEqual(repository.forks, 0)
        self.assertIsNone(repository.language)
        self.assertEqual(repository.topics, [])
        self.assertIsNone(repository.github_updated_at)
        self.assertIsNone(repository.fetched_at)
        self.assertIsNone(repository.refresh_status)

    def test_project_leader_can_remove_repository_connection(self):
        self.client.force_login(self.user)

        response = self.client.put(
            f"/api/v1/projects/{self.project.pk}",
            data=self.project_update_payload(repositoryUrl=""),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()["data"])
        self.assertFalse(Repository.objects.filter(project=self.project).exists())

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
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "SOSP")

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

    def test_project_delete_cascades_to_repository_and_members(self):
        repository_id = self.repository.pk
        member_id = self.member.pk

        Project.objects.filter(pk=self.project.pk).delete()

        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())
        self.assertFalse(Repository.objects.filter(pk=repository_id).exists())
        self.assertFalse(Member.objects.filter(pk=member_id).exists())

    def test_create_project_creates_leader_member_and_url_only_repository(self):
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
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(body["data"]["name"], "New Project")
        self.assertNotIn("teamName", body["data"])
        self.assertNotIn("teamId", body["data"])
        self.assertNotIn("leaderId", body["data"])
        self.assertNotIn("repositoryId", body["data"])
        self.assertNotIn("repositoryUrl", body["data"])
        self.assertEqual(body["data"]["status"], "ACTIVE")
        self.assertEqual(body["data"]["maxMembers"], 5)
        self.assertEqual(body["data"]["membershipRole"], "OWNER")
        self.assertEqual(
            body["data"]["repository"]["htmlUrl"],
            "https://github.com/example/new-project",
        )
        created_project = Project.objects.get(name="New Project")
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
        self.assertIsNone(repository.github_id)
        self.assertIsNone(repository.fetched_at)

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
        self.assertIsNone(body["data"]["repository"])
        self.assertEqual(body["data"]["maxMembers"], 5)
        project = Project.objects.get(name="Project Without Repository")
        self.assertEqual(project.max_members, 5)
        self.assertFalse(Repository.objects.filter(project=project).exists())
        self.assertTrue(project.members.get().is_leader)

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
            "projects.views.Member.objects.create",
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
        self.assertFalse(Project.objects.filter(name="Rollback Project").exists())

    def test_create_project_rolls_back_when_repository_creation_fails(self):
        self.client.force_login(self.user)

        with patch(
            "projects.views.Repository.objects.create",
            side_effect=IntegrityError,
        ):
            response = self.client.post(
                "/api/v1/projects/",
                data={
                    "name": "Repository Rollback Project",
                    "description": "Repository 생성 실패도 전체 등록을 롤백합니다.",
                    "repositoryUrl": "https://github.com/example/rollback",
                },
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(
            Project.objects.filter(name="Repository Rollback Project").exists()
        )
        self.assertFalse(
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

    def test_project_list_invalid_pagination_parameter(self):
        invalid_queries = (
            "start=-1&limit=10",
            "start=abc&limit=10",
            "start=0&limit=0",
        )
        for query in invalid_queries:
            with self.subTest(query=query):
                response = self.client.get(f"/api/v1/projects/?{query}")

                self.assertEqual(response.status_code, 400)
                body = response.json()
                self.assertEqual(body["status"], "INVALID_PAGINATION_PARAMETER")
                self.assertEqual(
                    body["detail"]["message"],
                    "start는 0 이상, limit은 1 이상이어야 합니다.",
                )
                self.assertEqual(body["detail"]["httpStatus"], 400)

    def project_update_payload(self, **overrides):
        payload = {
            "name": self.project.name,
            "description": self.project.description,
            "repositoryUrl": self.repository.html_url,
            "demoUrl": self.project.demo_url,
            "presentationUrl": self.project.presentation_url,
            "techStack": self.project.tech_stack,
            "usedOpenSource": self.project.used_open_source,
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
        response = self.client.get("/api/v1/projects/?joined=yes")

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["status"], "INVALID_PROJECT_FILTER")
        self.assertEqual(
            body["detail"]["message"],
            "joined는 true 또는 false여야 합니다.",
        )
        self.assertEqual(body["detail"]["httpStatus"], 400)

    def test_project_membership_history_requires_login(self):
        response = self.client.get("/api/v1/projects/members")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "PERMISSION_DENIED")

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
        self.assertIsNone(body["detail"])
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
        self.assertEqual(body["data"][0]["userId"], self.user.pk)
        self.assertIn("createdAt", body["data"][0])
        self.assertIn("updatedAt", body["data"][0])

    def test_project_membership_history_returns_empty_list(self):
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
            f"/api/v1/projects/{joined_project.pk}/members"
        )

        self.assertEqual(response.status_code, 200)
        joined_member.refresh_from_db()
        self.assertEqual(joined_member.status, Member.Status.LEFT)

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

    def create_projects_for_pagination(self, total):
        self.project.delete()
        base = timezone.now()
        created_projects = []

        for index in range(1, total + 1):
            project = Project.objects.create(
                name=f"Project {index}",
                description=f"Project {index} description",
                tech_stack=["React"],
                used_open_source=["Django REST framework"],
                status=Project.Status.ACTIVE,
            )
            created_projects.append(project)

        for index, project in enumerate(created_projects, start=1):
            Project.objects.filter(pk=project.pk).update(
                updated_at=base + timedelta(minutes=index)
            )
