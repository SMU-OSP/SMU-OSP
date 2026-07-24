from typing import Final

from django.core.exceptions import ValidationError
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
    MAX_REAPPLICATIONS: Final[int] = 5

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

    def has_available_member_slot(self):
        joined_members = getattr(self, "joined_members", None)
        joined_count = (
            len(joined_members)
            if joined_members is not None
            else self.members.filter(status=Member.Status.JOINED).count()
        )
        return joined_count < self.max_members

    def validate_membership_application(self, memberships):
        if self.status != self.Status.ACTIVE:
            raise ValidationError(
                "진행 중인 프로젝트에만 참가 신청할 수 있습니다.",
                code="invalid_project_status",
            )
        if any(
            membership.status in (Member.Status.PENDING, Member.Status.JOINED)
            for membership in memberships
        ):
            raise ValidationError(
                "이미 참가 신청 중이거나 참여 중인 프로젝트입니다.",
                code="membership_already_exists",
            )
        if len(memberships) > self.MAX_REAPPLICATIONS:
            raise ValidationError(
                f"재신청 가능 횟수 {self.MAX_REAPPLICATIONS}회를 모두 사용했습니다.",
                code="membership_reapplication_limit",
            )
        if not self.has_available_member_slot():
            raise ValidationError(
                "프로젝트 정원이 가득 차 참가 신청할 수 없습니다.",
                code="project_capacity_reached",
            )

    def set_status(self, status):
        allowed_transitions = {
            self.Status.ACTIVE: {
                self.Status.ACTIVE,
                self.Status.FINISHED,
                self.Status.INACTIVE,
                self.Status.DELETED,
            },
            self.Status.INACTIVE: {
                self.Status.INACTIVE,
                self.Status.DELETED,
            },
            self.Status.FINISHED: set(),
            self.Status.DELETED: set(),
        }
        if status not in allowed_transitions[self.status]:
            raise ValueError("현재 프로젝트 상태에서는 수정할 수 없습니다.")
        self.status = status

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

    def transition_to(self, next_status=None):
        allowed_transitions = {
            self.Status.PENDING: self.Status.CANCELED,
            self.Status.JOINED: self.Status.LEFT,
        }
        expected_status = allowed_transitions.get(self.status)
        if next_status is None:
            next_status = expected_status
        if expected_status is None or expected_status != next_status:
            raise ValidationError(
                "현재 상태에서는 신청 취소 또는 프로젝트 탈퇴를 할 수 없습니다.",
                code="invalid_member_status",
            )
        if self.is_leader and self.status == self.Status.JOINED:
            raise ValidationError(
                "프로젝트 팀장은 탈퇴할 수 없습니다.",
                code="leader_protected",
            )

        self.status = next_status

    def __str__(self):
        return f"{self.project} - {self.user_id or 'unknown'}"
