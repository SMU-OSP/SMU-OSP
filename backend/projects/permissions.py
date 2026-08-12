from __future__ import annotations

from django.core.exceptions import PermissionDenied

from .models import Member, Project


class ProjectPermissionDenied(PermissionDenied):
    """프로젝트 권한 거부 사유를 사용자 메시지와 함께 전달한다."""


def require_project_leader(
    *,
    project_id: int,
    user_id: int,
    denied_message: str,
) -> None:
    """사용자의 프로젝트 팀장 권한을 확인한다.

    Args:
        project_id: 권한을 확인할 프로젝트 ID.
        user_id: 요청 사용자 ID.
        denied_message: 권한이 없을 때 사용자에게 반환할 메시지.

    Raises:
        Project.DoesNotExist: 프로젝트가 존재하지 않는 경우.
        ProjectPermissionDenied: 요청자가 프로젝트 팀장이 아닌 경우.
    """
    is_leader = Member.objects.filter(
        project_id=project_id,
        user_id=user_id,
        status=Member.Status.JOINED,
        is_leader=True,
    ).exists()
    if is_leader:
        return
    if not Project.objects.filter(pk=project_id).exists():
        raise Project.DoesNotExist
    raise ProjectPermissionDenied(denied_message)


def require_project_member_access(
    *,
    project_id: int,
    user_id: int,
    manage: bool,
) -> None:
    """프로젝트 멤버 목록 조회 권한을 확인한다.

    Args:
        project_id: 권한을 확인할 프로젝트 ID.
        user_id: 요청 사용자 ID.
        manage: 멤버 관리 목록을 요청하는지 여부.

    Raises:
        ProjectPermissionDenied: 멤버 조회 권한이 없는 경우.
    """
    memberships = Member.objects.filter(
        project_id=project_id,
        project__status__in=(
            Project.Status.ACTIVE,
            Project.Status.INACTIVE,
            Project.Status.FINISHED,
        ),
        user_id=user_id,
        status=Member.Status.JOINED,
    )
    if manage:
        memberships = memberships.filter(is_leader=True)
    if not memberships.exists():
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
