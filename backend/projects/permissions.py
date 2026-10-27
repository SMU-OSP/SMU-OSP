from __future__ import annotations

from functools import partial

from django.core.exceptions import PermissionDenied

from .models import Member, Project


class ProjectPermissionDenied(PermissionDenied):
    """프로젝트 권한 거부 사유를 사용자 메시지와 함께 전달한다."""


def require_project_access(
    *,
    project_id: int,
    user_id: int,
    manage: bool,
) -> None:
    """사용자의 프로젝트 접근 권한을 확인한다.

    Args:
        project_id: 권한을 확인할 프로젝트 ID.
        user_id: 요청 사용자 ID.
        manage: 팀장 권한이 필요한지 여부.

    Raises:
        ProjectPermissionDenied: 요청자에게 필요한 프로젝트 권한이 없는 경우.
    """
    memberships = Member.objects.filter(
        project_id=project_id,
        user_id=user_id,
        status=Member.Status.JOINED,
    )
    if manage:
        memberships = memberships.filter(is_leader=True)
    if not memberships.exists():
        raise ProjectPermissionDenied("프로젝트 접근 권한이 없습니다.")


require_project_member_access = partial(require_project_access, manage=False)
require_project_leader = partial(require_project_access, manage=True)


def can_edit_project(*, project: Project, member: Member) -> bool:
    """참여 중인 팀장이 진행 중인 프로젝트를 수정할 수 있는지 반환한다.

    Args:
        project: 수정 가능 여부를 표시할 프로젝트.
        member: 요청자의 참여 중인 멤버십.

    Returns:
        진행 중인 프로젝트의 팀장이면 True, 아니면 False.
    """
    return project.status == Project.Status.ACTIVE and member.is_leader
