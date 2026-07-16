from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Team, TeamMember


class TeamDataStructureTests(TestCase):
    def test_team_and_member_data_structure_is_preserved(self):
        user = get_user_model().objects.create_user(
            username="team-leader",
            password="password",
            github_email="team-leader@example.com",
            name="팀장",
            student_id=1,
            major="IT공학",
        )
        team = Team.objects.create(
            name="Project Team",
            description="프로젝트 내부 팀",
            logo_url="https://example.com/logo.png",
            leader=user,
            leader_name="팀장",
        )
        member = TeamMember.objects.create(
            team=team,
            user=user,
            name="팀원",
            role="개발",
            github_id="member",
            email="member@example.com",
        )

        self.assertEqual(team.logo_url, "https://example.com/logo.png")
        self.assertEqual(team.leader_name, "팀장")
        self.assertEqual(member.status, TeamMember.Status.ACTIVE)
        self.assertEqual(team.members.get(), member)
