from datetime import timedelta
from typing import Final

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from common.models import CommonModel


def get_default_max_members():
    return settings.PROJECT_DEFAULT_MAX_MEMBERS


class Repository(CommonModel):
    project = models.OneToOneField(
        "Project",
        on_delete=models.CASCADE,
        related_name="repository",
    )
    github_id = models.PositiveBigIntegerField(unique=True)
    name = models.CharField(max_length=150)
    full_name = models.CharField(max_length=300)
    html_url = models.URLField(max_length=500)

    def __str__(self):
        return self.full_name


class RepositorySnapshot(models.Model):
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="snapshots",
    )
    date = models.DateField()
    pull_requests = models.PositiveIntegerField(default=0)
    commits = models.PositiveIntegerField(default=0)
    stars = models.PositiveIntegerField(default=0)
    forks = models.PositiveIntegerField(default=0)
    has_code_changed = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("repository", "date"),
                name="repository_snapshot_date_uniq",
            ),
        ]


class RepositoryLanguage(models.Model):
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="languages",
    )
    language = models.CharField(max_length=100)
    bytes = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("repository", "language"),
                name="repository_language_uniq",
            ),
        ]


class RepositoryStatus(models.Model):
    repository = models.OneToOneField(
        Repository,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="status",
    )
    current_streak = models.PositiveIntegerField(default=0)
    max_streak = models.PositiveIntegerField(default=0)
    description = models.TextField(null=True, blank=True)
    last_status_code = models.CharField(max_length=30)
    fetched_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


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
                self.Status.ACTIVE,
                self.Status.DELETED,
            },
            self.Status.FINISHED: {
                self.Status.DELETED,
            },
            self.Status.DELETED: set(),
        }
        if status not in allowed_transitions[self.status]:
            raise ValueError("현재 프로젝트 상태에서는 수정할 수 없습니다.")
        self.status = status
        if status in {self.Status.FINISHED, self.Status.DELETED}:
            self.members.filter(status=Member.Status.PENDING).update(
                status=Member.Status.CANCELED,
                updated_at=timezone.now(),
            )

    def deactivate_if_repository_inactive(self, snapshot_date):
        if self.status != self.Status.ACTIVE:
            return False

        repository = getattr(self, "repository", None)
        if repository is None:
            return False
        snapshots = list(
            repository.snapshots.order_by("-date").values_list(
                "date",
                "has_code_changed",
            )[:30]
        )
        expected_dates = [
            snapshot_date - timedelta(days=offset)
            for offset in range(30)
        ]
        if len(snapshots) != 30 or any(
            date != expected_date or has_code_changed
            for (date, has_code_changed), expected_date in zip(
                snapshots,
                expected_dates,
            )
        ):
            return False

        self.set_status(self.Status.INACTIVE)
        return True

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
    joined_at = models.DateTimeField(null=True, blank=True)

    def transition_to(
        self,
        next_status=None,
        *,
        description=None,
        update_description=False,
        require_description=False,
    ):
        allowed_transitions = {
            self.Status.PENDING: {
                self.Status.CANCELED,
                self.Status.DECLINED,
                self.Status.JOINED,
            },
            self.Status.JOINED: {self.Status.LEFT},
        }
        if next_status is None:
            next_status = {
                self.Status.PENDING: self.Status.CANCELED,
                self.Status.JOINED: self.Status.LEFT,
            }.get(self.status)
        if next_status not in allowed_transitions.get(self.status, set()):
            raise ValidationError(
                f"{self.status} 상태에서는 {next_status}(으)로 변경할 수 없습니다.",
                code="invalid_member_status",
            )
        if self.is_leader and next_status == self.Status.LEFT:
            raise ValidationError(
                "프로젝트 팀장은 탈퇴하거나 내보낼 수 없습니다.",
                code="leader_protected",
            )
        if require_description and not (description or "").strip():
            raise ValidationError(
                "멤버를 내보내려면 사유를 입력해주세요.",
                code="member_description_required",
            )
        if (
            next_status == self.Status.JOINED
            and not self.project.has_available_member_slot()
        ):
            raise ValidationError(
                "프로젝트 정원이 가득 차 신청을 승인할 수 없습니다.",
                code="project_capacity_reached",
            )

        self.status = next_status
        if next_status == self.Status.JOINED:
            self.joined_at = timezone.now()
        if update_description:
            self.description = description

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
