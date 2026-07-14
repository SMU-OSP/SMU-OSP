from django.test import TestCase

from .models import Team


class TeamApiTests(TestCase):
    def test_create_team_response_shape(self):
        response = self.client.post(
            "/api/v1/teams/",
            data={
                "name": "SOSP Team",
                "description": "팀 프로젝트 등록 구조를 구성하는 팀입니다.",
                "logoUrl": "",
                "members": [
                    {
                        "name": "권지연",
                        "role": "프론트엔드",
                        "githubId": "Jiyeon125",
                        "email": "0215wldus@sookmyung.ac.kr",
                    }
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertIsNone(body["detail"])
        self.assertEqual(body["data"]["name"], "SOSP Team")
        self.assertEqual(body["data"]["leaderName"], "권지연")
        self.assertEqual(body["data"]["members"][0]["githubId"], "Jiyeon125")

    def test_create_team_allows_blank_optional_member_fields(self):
        response = self.client.post(
            "/api/v1/teams/",
            data={
                "name": "SOSP Team",
                "description": "",
                "logoUrl": "",
                "members": [
                    {
                        "name": "권지연",
                        "role": "프론트엔드",
                        "githubId": "",
                        "email": "",
                    }
                ],
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertIsNone(body["data"]["members"][0]["githubId"])
        self.assertIsNone(body["data"]["members"][0]["email"])

    def test_list_team_response_shape(self):
        team = Team.objects.create(name="SOSP Team", leader_name="권지연")
        team.members.create(name="권지연", role="프론트엔드")

        response = self.client.get("/api/v1/teams/")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(body["data"][0]["id"], team.pk)
        self.assertEqual(body["data"][0]["members"][0]["name"], "권지연")

    def test_team_detail_not_found(self):
        response = self.client.get("/api/v1/teams/999")

        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertEqual(body["status"], "TEAM_NOT_FOUND")
        self.assertIsNone(body["data"])
        self.assertEqual(body["detail"]["httpStatus"], 404)

    def test_create_team_requires_member(self):
        response = self.client.post(
            "/api/v1/teams/",
            data={"name": "SOSP Team", "members": []},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["status"], "REQUIRED_FIELD_MISSING")
        self.assertIsNone(body["data"])
