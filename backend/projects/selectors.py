from django.db.models import Exists, OuterRef, Prefetch, Q

from .models import (
    Member,
    Project,
    ProjectLanguage,
    RepositoryLanguage,
    RepositorySnapshot,
)


def list_projects(
    *,
    start: int,
    limit: int,
    joined: bool,
    owned: bool,
    keyword: str | None,
    languages: tuple[str, ...],
    status: str | None,
    sort: str,
    user_id: int | None,
) -> tuple[list[Project], int]:
    """필터링된 프로젝트 한 페이지와 전체 결과 수를 반환한다.

    삭제된 프로젝트는 항상 제외하고, status가 없으면 완료된 프로젝트도
    제외한다. joined는 일반 팀원 프로젝트, owned는 팀장 프로젝트를 선택하며
    둘 다 참이면 두 범위를 모두 포함한다. 여러 languages 조건은 OR로
    결합한다. sort='name'이면 이름순, 그 외 허용값은 최신 수정순이다.
    """
    projects = (
        Project.objects.select_related("repository", "repository__status")
        .prefetch_related(
            "languages",
            Prefetch(
                "repository__snapshots",
                queryset=RepositorySnapshot.objects.order_by("-date")[:1],
                to_attr="serialized_snapshots",
            ),
            Prefetch(
                "repository__languages",
                queryset=RepositoryLanguage.objects.order_by(
                    "-bytes",
                    "language",
                ),
                to_attr="serialized_languages",
            ),
        )
        .exclude(status=Project.Status.DELETED)
        .order_by("-updated_at", "-pk")
    )

    if joined or owned:
        membership_filter = Q(
            members__user_id=user_id,
            members__status=Member.Status.JOINED,
        )
        if joined != owned:
            membership_filter &= Q(members__is_leader=owned)
        projects = projects.filter(membership_filter).distinct()

    if not status:
        projects = projects.exclude(status=Project.Status.FINISHED)
    if keyword:
        projects = projects.filter(
            Q(name__icontains=keyword)
            | Q(description__icontains=keyword)
        )
    if languages:
        language_filter = Q()
        for language in languages:
            language_filter |= Q(name__iexact=language)
        project_language_matches = ProjectLanguage.objects.filter(
            projects=OuterRef("pk")
        ).filter(language_filter)
        projects = projects.annotate(
            has_matching_filtered_project_language=Exists(
                project_language_matches
            )
        ).filter(has_matching_filtered_project_language=True)
    if status:
        projects = projects.filter(status=status)
    if sort == "name":
        projects = projects.order_by("name", "pk")

    if user_id is not None:
        projects = projects.prefetch_related(
            Prefetch(
                "members",
                queryset=Member.objects.filter(
                    user_id=user_id,
                    status=Member.Status.JOINED,
                ).order_by("-is_leader"),
                to_attr="request_user_memberships",
            )
        )

    count = projects.count()
    projects = list(projects[start : start + limit])
    return projects, count


def get_project_detail(
    *,
    project_id: int,
) -> Project:
    """삭제되지 않은 프로젝트와 상세 응답에 필요한 관계를 조회한다.

    참여 중인 멤버, 프로젝트 언어, Repository 상태, 최신 Snapshot과
    Repository 언어를 함께 조회한다. 프로젝트가 없거나 삭제된 상태라면
    Project.DoesNotExist를 발생시킨다.
    """
    joined_members = (
        Member.objects.filter(status=Member.Status.JOINED)
        .select_related("user")
        .order_by("-is_leader", "created_at", "pk")
    )
    project = (
        Project.objects.select_related(
            "repository",
            "repository__status",
        )
        .prefetch_related(
            "languages",
            Prefetch(
                "members",
                queryset=joined_members,
                to_attr="joined_members",
            ),
            Prefetch(
                "repository__snapshots",
                queryset=RepositorySnapshot.objects.order_by("-date")[:1],
                to_attr="serialized_snapshots",
            ),
            Prefetch(
                "repository__languages",
                queryset=RepositoryLanguage.objects.order_by(
                    "-bytes",
                    "language",
                ),
                to_attr="serialized_languages",
            ),
        )
        .exclude(status=Project.Status.DELETED)
        .get(pk=project_id)
    )

    return project


def list_memberships_for_user(*, user_id: int) -> list[Member]:
    """사용자의 팀장 이외 멤버십 이력을 최신순으로 반환한다.

    삭제된 프로젝트의 멤버십은 제외하고, 연관된 프로젝트를 함께 조회한다.
    """
    return list(
        Member.objects.select_related("project")
        .filter(user_id=user_id, is_leader=False)
        .exclude(project__status=Project.Status.DELETED)
        .order_by("-created_at", "-pk")
    )


def get_joined_project_member(
    *,
    project_id: int,
    user_id: int,
) -> Member | None:
    """프로젝트에 참여 중인 사용자의 멤버십을 반환한다.

    참여 중인 행이 여러 개라면 팀장 행을 우선하고, 그 외에는 가장 최근 행을
    반환한다. 참여 중인 멤버십이 없으면 None을 반환한다.
    """
    return (
        Member.objects.filter(
            project_id=project_id,
            user_id=user_id,
            status=Member.Status.JOINED,
        )
        .order_by("-is_leader", "-created_at", "-pk")
        .first()
    )


def list_project_members(
    *,
    project_id: int,
    manage: bool,
) -> list[Member]:
    """프로젝트 멤버를 팀장 우선, 최신순으로 반환한다.

    manage=False이면 참여 중인 멤버만 반환하고, manage=True이면 관리 화면을
    위해 모든 멤버십 상태를 포함한다. 연관된 사용자도 함께 조회한다.
    """
    members = Member.objects.filter(project_id=project_id).select_related(
        "user"
    )
    if not manage:
        members = members.filter(status=Member.Status.JOINED)
    return list(members.order_by("-is_leader", "-created_at", "-pk"))
