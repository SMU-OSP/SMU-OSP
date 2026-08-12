from __future__ import annotations

from django.core.exceptions import PermissionDenied

from .models import Member, Project


class ProjectPermissionDenied(PermissionDenied):
    """프로젝트 권한 거부 사유를 사용자 메시지와 함께 전달한다."""


def require_project_leader(
    *,
    actor_is_leader: bool,
    denied_message: str,
) -> None:
    """조회된 팀장 권한 결과를 검사한다.

    Args:
        actor_is_leader: 요청자가 참여 중인 프로젝트 팀장인지 여부.
        denied_message: 권한이 없을 때 사용자에게 반환할 메시지.

    Raises:
        ProjectPermissionDenied: 요청자가 프로젝트 팀장이 아닌 경우.
    """
    if not actor_is_leader:
        raise ProjectPermissionDenied(denied_message)


def require_project_member_access(
    *,
    member: Member | None,
    manage: bool,
) -> None:
    """프로젝트 멤버 목록 조회 권한을 확인한다.

    Args:
        member: 요청자의 참여 중인 프로젝트 멤버십.
        manage: 전체 멤버십 관리 목록을 요청하는지 여부.

    Raises:
        ProjectPermissionDenied: 참여 중이 아니거나 관리 요청자가 팀장이
            아닌 경우.
    """
    if member is None or (manage and not member.is_leader):
        raise ProjectPermissionDenied("프로젝트 멤버 조회 권한이 없습니다.")


def can_edit_project(*, project: Project, member: Member) -> bool:
    """참여 중인 팀장이 진행 중인 프로젝트를 수정할 수 있는지 반환한다.

    Args:
        project: 수정 가능 여부를 표시할 프로젝트.
        member: 요청자의 참여 중인 멤버십.

    Returns:
        진행 중인 프로젝트의 팀장이면 True, 아니면 False.
    """
    return project.status == Project.Status.ACTIVE and member.is_leader
