from django.conf import settings
from django.db import models

from common.models import CommonModel


class Team(CommonModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    logo_url = models.URLField(max_length=500, null=True, blank=True)
    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leading_teams",
    )
    leader_name = models.CharField(max_length=100, default="")

    def __str__(self):
        return self.name


class TeamMember(CommonModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="members")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="team_memberships",
    )
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    github_id = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.team} - {self.name}"
