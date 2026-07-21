from django.conf import settings
from django.db import models

from common.models import CommonModel


def get_default_max_members():
    return settings.PROJECT_DEFAULT_MAX_MEMBERS


class Repository(CommonModel):
    class RefreshStatus(models.TextChoices):
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    project = models.OneToOneField(
        "Project",
        on_delete=models.CASCADE,
        related_name="repository",
    )
    github_id = models.PositiveBigIntegerField(null=True, blank=True, unique=True)
    name = models.CharField(max_length=150)
    full_name = models.CharField(max_length=300)
    description = models.TextField(null=True, blank=True)
    stars = models.PositiveIntegerField(default=0)
    forks = models.PositiveIntegerField(default=0)
    language = models.CharField(max_length=100, null=True, blank=True)
    topics = models.JSONField(default=list, blank=True)
    html_url = models.URLField(max_length=500)
    github_updated_at = models.DateTimeField(null=True, blank=True)
    fetched_at = models.DateTimeField(null=True, blank=True)
    refresh_status = models.CharField(
        max_length=30,
        choices=RefreshStatus.choices,
        null=True,
        blank=True,
    )
    last_error_code = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.full_name


class Project(CommonModel):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        FINISHED = "FINISHED", "Finished"
        INACTIVE = "INACTIVE", "Inactive"
        DELETED = "DELETED", "Deleted"

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    demo_url = models.URLField(max_length=500, null=True, blank=True)
    presentation_url = models.URLField(max_length=500, null=True, blank=True)
    tech_stack = models.JSONField(default=list, blank=True)
    used_open_source = models.JSONField(default=list, blank=True)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    max_members = models.PositiveIntegerField(default=get_default_max_members)

    def __str__(self):
        return self.name


class Member(CommonModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CANCELED = "CANCELED", "Canceled"
        DECLINED = "DECLINED", "Declined"
        JOINED = "JOINED", "Joined"
        LEFT = "LEFT", "Left"

    id = models.BigAutoField(primary_key=True)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="members",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project_memberships",
    )
    is_leader = models.BooleanField(default=False)
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )
    description = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("project", "id"),
                name="project_member_project_id_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=("project", "status"),
                name="project_member_status_idx",
            ),
            models.Index(
                fields=("user", "status"),
                name="user_member_status_idx",
            ),
        ]

    def __str__(self):
        return f"{self.project} - {self.user_id or 'unknown'}"
