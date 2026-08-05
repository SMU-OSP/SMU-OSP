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
        leader_member: 생성된 팀장 멤버십.
        repository_error: Repository 등록 실패 오류. 성공하면 None.
    """

    project: Project
    leader_member: Member
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
    project: Project,
    repository_url: str | None,
) -> GitHubRepositoryIdentity | None:
    repository = getattr(project, "repository", None)
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
        leader_member = Member.objects.create(
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
        leader_member=leader_member,
        repository_error=repository_error,
    )
