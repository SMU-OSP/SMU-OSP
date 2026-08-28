from collections.abc import Sequence
from dataclasses import dataclass

from django.db import IntegrityError, transaction

from users.models import User

from .github_client import (
    GitHubClientError,
    GitHubErrorCode,
    GitHubRepositoryIdentity,
    fetch_repository_identity,
    parse_repository_url,
)
from .models import Member, Project, ProjectLanguage, Repository
from .tasks import enqueue_repository_refresh

REPOSITORY_ALREADY_LINKED_MESSAGE = (
    "이미 다른 프로젝트에 연결된 Repository입니다."
)
REPOSITORY_CHANGE_NOT_ALLOWED_MESSAGE = (
    "이미 등록된 Repository는 변경하거나 연결 해제할 수 없습니다."
)
REPOSITORY_INVALID_MESSAGE = (
    "존재하는 공개 GitHub Repository URL을 입력해주세요."
)
REPOSITORY_LOOKUP_FAILED_MESSAGE = (
    "GitHub Repository 정보를 불러오지 못했습니다. 잠시 후 다시 시도해주세요."
)
REPOSITORY_SAVE_FAILED_MESSAGE = (
    "Repository를 등록하지 못했습니다. 잠시 후 다시 시도해주세요."
)


class RepositoryRegistrationError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


class ProjectCreationError(ValueError):
    """프로젝트 생성 중 예상 가능한 입력 충돌을 나타낸다."""


@dataclass(frozen=True)
class ProjectCreationResult:
    """프로젝트 생성 결과와 비치명적 Repository 등록 오류를 나타낸다.

    Attributes:
        project: 생성된 프로젝트.
        repository_error: Repository 등록 실패 오류. 성공하면 None.
    """

    project: Project
    repository_error: RepositoryRegistrationError | None


def _registration_error(
    error: GitHubClientError,
) -> RepositoryRegistrationError:
    code, message = {
        GitHubErrorCode.INVALID_URL: (
            "INVALID_GITHUB_URL",
            REPOSITORY_INVALID_MESSAGE,
        ),
        GitHubErrorCode.REPOSITORY_NOT_FOUND: (
            "GITHUB_REPOSITORY_NOT_FOUND",
            REPOSITORY_INVALID_MESSAGE,
        ),
        GitHubErrorCode.PRIVATE_REPOSITORY: (
            "PRIVATE_REPOSITORY",
            REPOSITORY_INVALID_MESSAGE,
        ),
        GitHubErrorCode.RATE_LIMIT_EXCEEDED: (
            "GITHUB_RATE_LIMIT_EXCEEDED",
            REPOSITORY_LOOKUP_FAILED_MESSAGE,
        ),
        GitHubErrorCode.API_FAILED: (
            "GITHUB_API_FAILED",
            REPOSITORY_LOOKUP_FAILED_MESSAGE,
        ),
    }[error.code]
    return RepositoryRegistrationError(code, message)


def prepare_repository_registration(
    repository_url: str,
) -> GitHubRepositoryIdentity:
    try:
        full_name = parse_repository_url(repository_url)
    except GitHubClientError as error:
        raise _registration_error(error) from error
    if Repository.objects.filter(full_name__iexact=full_name).exists():
        raise RepositoryRegistrationError(
            "INVALID_PROJECT_INPUT",
            REPOSITORY_ALREADY_LINKED_MESSAGE,
        )

    try:
        data = fetch_repository_identity(full_name)
    except GitHubClientError as error:
        raise _registration_error(error) from error
    if Repository.objects.filter(github_id=data.github_id).exists():
        raise RepositoryRegistrationError(
            "INVALID_PROJECT_INPUT",
            REPOSITORY_ALREADY_LINKED_MESSAGE,
        )
    return data


def prepare_project_repository_update(
    project_id: int,
    repository_url: str | None,
) -> GitHubRepositoryIdentity | None:
    repository = Repository.objects.filter(project_id=project_id).first()
    if repository is not None:
        if repository_url != repository.html_url:
            raise ValueError(REPOSITORY_CHANGE_NOT_ALLOWED_MESSAGE)
        return None
    if not repository_url:
        return None
    return prepare_repository_registration(repository_url)


def update_project_repository(
    project: Project,
    repository_url: str | None,
    *,
    previous_project_status: str | None = None,
    repository_data: GitHubRepositoryIdentity | None = None,
) -> None:
    repository = getattr(project, "repository", None)
    if repository:
        if repository_url != repository.html_url:
            raise ValueError(REPOSITORY_CHANGE_NOT_ALLOWED_MESSAGE)
        if (
            previous_project_status == project.Status.INACTIVE
            and project.status == project.Status.ACTIVE
        ):
            transaction.on_commit(
                lambda: enqueue_repository_refresh(repository.pk),
                robust=True,
            )
        return
    if not repository_url:
        return

    data = repository_data or prepare_repository_registration(repository_url)
    if Repository.objects.filter(full_name__iexact=data.full_name).exists():
        raise RepositoryRegistrationError(
            "INVALID_PROJECT_INPUT",
            REPOSITORY_ALREADY_LINKED_MESSAGE,
        )
    if Repository.objects.filter(github_id=data.github_id).exists():
        raise RepositoryRegistrationError(
            "INVALID_PROJECT_INPUT",
            REPOSITORY_ALREADY_LINKED_MESSAGE,
        )

    try:
        repository = Repository.objects.create(
            project=project,
            github_id=data.github_id,
            name=data.name,
            full_name=data.full_name,
            html_url=data.html_url,
        )
    except IntegrityError as error:
        raise RepositoryRegistrationError(
            "INTERNAL_SERVER_ERROR",
            REPOSITORY_SAVE_FAILED_MESSAGE,
        ) from error
    transaction.on_commit(
        lambda: enqueue_repository_refresh(repository.pk),
        robust=True,
    )


def create_project(
    *,
    actor: User,
    name: str,
    description: str,
    repository_url: str | None,
    demo_url: str | None,
    presentation_url: str | None,
    languages: Sequence[ProjectLanguage],
) -> ProjectCreationResult:
    """프로젝트와 팀장 멤버십을 생성하고 Repository 등록을 시도한다.

    Repository 등록 실패는 프로젝트 생성을 롤백하지 않고 결과에 담아
    반환한다. GitHub 조회는 프로젝트 생성 트랜잭션이 끝난 뒤 수행한다.

    Args:
        actor: 프로젝트를 생성하는 사용자.
        name: 프로젝트명.
        description: 프로젝트 설명.
        repository_url: 연결할 Repository URL.
        demo_url: 결과물 URL.
        presentation_url: 발표 자료 URL.
        languages: 프로젝트에 연결할 사용 언어.

    Returns:
        생성된 프로젝트와 Repository 등록 오류를 담은 결과.

    Raises:
        ProjectCreationError: 이미 등록된 프로젝트명인 경우.
        IntegrityError: 언어 또는 팀장 멤버십 저장에 실패한 경우.
    """
    with transaction.atomic():
        try:
            project = Project.objects.create(
                name=name,
                description=description,
                demo_url=demo_url,
                presentation_url=presentation_url,
            )
        except IntegrityError as error:
            raise ProjectCreationError(
                "이미 등록된 프로젝트명입니다."
            ) from error
        project.languages.set(languages)
        Member.objects.create(
            project=project,
            user=actor,
            is_leader=True,
            status=Member.Status.JOINED,
        )

    repository_error: RepositoryRegistrationError | None = None
    try:
        update_project_repository(project, repository_url)
    except RepositoryRegistrationError as error:
        repository_error = error

    return ProjectCreationResult(
        project=project,
        repository_error=repository_error,
    )


def create_membership_application(
    *,
    actor: User,
    project_id: int,
) -> None:
    """프로젝트 참가 신청을 PENDING 멤버십으로 생성한다.

    Project 행을 잠근 트랜잭션에서 과거 신청 이력을 다시 조회하고 신청
    가능 여부를 검증해 같은 프로젝트의 동시 신청을 순차 처리한다.

    Args:
        actor: 참가 신청을 요청한 사용자.
        project_id: 참가 신청 대상 프로젝트 ID.

    Raises:
        Project.DoesNotExist: 프로젝트가 없거나 삭제된 경우.
        ValidationError: 프로젝트에 참가 신청할 수 없는 경우.
    """
    with transaction.atomic():
        project = (
            Project.objects.exclude(status=Project.Status.DELETED)
            .select_for_update()
            .get(pk=project_id)
        )
        memberships = list(
            Member.objects.filter(
                project=project,
                user=actor,
            )
        )
        project.validate_membership_application(memberships)
        Member.objects.create(
            project=project,
            user=actor,
            status=Member.Status.PENDING,
        )


def get_membership_cancel_target(
    *,
    actor: User,
    project_id: int,
) -> Member:
    """취소·탈퇴 입력 검증 전에 대상 존재와 구조적 전이 가능 여부를 확인한다.

    삭제된 프로젝트는 멤버십이 남아 있어도 404로 거절한다. 사유(description)
    검사는 body 파싱 이후 `cancel_or_leave_membership()`에서 수행한다.

    Args:
        actor: 신청 취소 또는 탈퇴를 요청한 사용자.
        project_id: 대상 프로젝트 ID.

    Returns:
        기본 상태 전이가 가능한 최신 멤버십. 팀장 멤버십을 우선한다.

    Raises:
        Project.DoesNotExist: 프로젝트가 없거나 삭제된 경우.
        Member.DoesNotExist: 사용자의 멤버십 이력이 없는 경우.
        ValidationError: 팀장 보호 또는 현재 상태에서 전이할 수 없는 경우.
    """
    Project.objects.exclude(status=Project.Status.DELETED).get(pk=project_id)
    membership = (
        Member.objects.filter(project_id=project_id, user=actor)
        .order_by("-is_leader", "-created_at", "-pk")
        .first()
    )
    if membership is None:
        raise Member.DoesNotExist
    membership.assert_transition_structure()
    return membership


def cancel_or_leave_membership(
    *,
    actor: User,
    project_id: int,
    description: str | None,
    update_description: bool,
) -> None:
    """최신 참가 신청을 취소하거나 일반 팀원이 프로젝트에서 탈퇴한다.

    호출 전에 `get_membership_cancel_target()`으로 대상과 구조적 전이
    가능 여부를 확인하는 것을 전제로 한다. 팀장 멤버십을 우선 조회해
    이후에 생성된 신청 이력이 있더라도 팀장 보호 규칙을 우회하지 못하게
    한다. update_description이 참이면 description이 None인 경우도
    저장하고, 거짓이면 기존 사유를 유지한다.

    Args:
        actor: 신청 취소 또는 탈퇴를 요청한 사용자.
        project_id: 대상 프로젝트 ID.
        description: 탈퇴 사유. 신청 취소와 자진 탈퇴에서는 선택 사항이다.
        update_description: description 필드를 갱신할지 여부.

    Raises:
        Project.DoesNotExist: 프로젝트가 없거나 삭제된 경우.
        Member.DoesNotExist: 사용자의 멤버십 이력이 없는 경우.
        ValidationError: 현재 멤버십 상태에서 전이할 수 없는 경우.
    """
    with transaction.atomic():
        Project.objects.exclude(
            status=Project.Status.DELETED,
        ).select_for_update().get(pk=project_id)
        membership = (
            Member.objects.select_for_update()
            .filter(project_id=project_id, user=actor)
            .order_by("-is_leader", "-created_at", "-pk")
            .first()
        )
        if membership is None:
            raise Member.DoesNotExist

        membership.transition_to(
            description=description,
            update_description=update_description,
        )
        membership.save(
            update_fields=(
                "status",
                "description",
                "joined_at",
                "updated_at",
            )
        )


def change_project_member_status(
    *,
    project_id: int,
    member_id: int,
    next_status: str,
    description: str | None,
    update_description: bool,
) -> None:
    """프로젝트 멤버의 상태를 잠금 구간에서 변경한다.

    Project를 먼저 잠근 뒤 대상 Member를 잠가 승인 시 정원 검사와 상태
    변경이 같은 트랜잭션에서 수행되도록 한다. Member에는 잠긴 Project
    인스턴스를 연결해 정원 검사 중 관계를 다시 조회하지 않는다.

    Args:
        project_id: 대상 프로젝트 ID.
        member_id: 상태를 변경할 멤버십 ID.
        next_status: 변경할 멤버 상태.
        description: 반려 또는 내보내기 사유.
        update_description: description 필드 갱신 여부.

    Raises:
        Project.DoesNotExist: 프로젝트가 없거나 삭제된 경우.
        Member.DoesNotExist: 변경 가능한 일반 멤버가 존재하지 않는 경우.
        ValidationError: 상태 전이 조건을 만족하지 않는 경우.
    """
    with transaction.atomic():
        project = (
            Project.objects.exclude(status=Project.Status.DELETED)
            .select_for_update()
            .get(pk=project_id)
        )
        member = (
            Member.objects.select_for_update()
            .get(project_id=project_id, pk=member_id, is_leader=False)
        )
        member.project = project
        if next_status == Member.Status.LEFT:
            member.remove_from_project(description=description)
        else:
            member.transition_to(
                next_status,
                description=description,
                update_description=update_description,
            )
        member.save(
            update_fields=(
                "status",
                "description",
                "joined_at",
                "updated_at",
            )
        )
