from django.conf import settings
from django.db import models

from common.models import CommonModel


class Team(CommonModel):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(null=True, blank=True)
    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leading_teams",
    )

    def __str__(self):
        return self.name
