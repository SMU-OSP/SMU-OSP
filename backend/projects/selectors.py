from django.db.models import Count, Exists, OuterRef, Prefetch, Q

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

    삭제된 프로젝트는 항상 제외한다.

    Args:
        start: 조회를 시작할 결과 위치.
        limit: 반환할 최대 프로젝트 수.
        joined: 일반 팀원으로 참여한 프로젝트만 조회할지 여부.
        owned: 팀장으로 참여한 프로젝트만 조회할지 여부.
        keyword: 프로젝트명과 설명에 적용할 검색어.
        languages: 하나 이상 일치하면 포함할 프로젝트 언어 목록.
        status: 조회할 프로젝트 상태. 없으면 완료 프로젝트를 제외한다.
        sort: 이름순 또는 최신 수정순을 선택하는 정렬 기준.
        user_id: 멤버십 범위와 요청자 정보를 조회할 사용자 ID.

    Returns:
        현재 페이지의 프로젝트 목록과 모든 필터에 일치하는 전체 결과 수.
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
    project_id: int,
    user_id: int | None = None,
) -> Project:
    """삭제되지 않은 프로젝트와 상세 응답에 필요한 관계를 조회한다.

    참여 중인 멤버, 프로젝트 언어, Repository 상태, 최신 Snapshot과
    Repository 언어를 함께 조회한다.

    Args:
        project_id: 조회할 프로젝트 ID.
        user_id: 현재 프로젝트의 신청 상태를 함께 조회할 사용자 ID.

    Returns:
        상세 응답에 필요한 관계가 미리 조회된 프로젝트.

    Raises:
        Project.DoesNotExist: 프로젝트가 없거나 삭제된 경우.
    """
    joined_members = (
        Member.objects.filter(status=Member.Status.JOINED)
        .select_related("user")
        .order_by("-is_leader", "created_at", "pk")
    )
    prefetches = [
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
    ]
    if user_id is not None:
        prefetches.append(
            Prefetch(
                "members",
                queryset=Member.objects.filter(user_id=user_id).order_by(
                    "-created_at",
                    "-pk",
                ),
                to_attr="request_user_application_history",
            )
        )

    project = (
        Project.objects.select_related(
            "repository",
            "repository__status",
        )
        .annotate(
            pending_member_count=Count(
                "members",
                filter=Q(members__status=Member.Status.PENDING),
            )
        )
        .prefetch_related(*prefetches)
        .exclude(status=Project.Status.DELETED)
        .get(pk=project_id)
    )

    return project


def list_memberships_for_user(
    *,
    user_id: int,
    start: int,
    limit: int,
    statuses: tuple[str, ...],
    sort: str,
) -> tuple[list[Member], int]:
    """사용자의 팀장 이외 멤버십 이력 한 페이지를 반환한다.

    삭제된 프로젝트의 멤버십은 제외하고 상태와 정렬 조건을 적용한다.

    Args:
        user_id: 멤버십 이력을 조회할 사용자 ID.
        start: 조회를 시작할 결과 위치.
        limit: 반환할 최대 멤버십 수.
        statuses: 조회할 멤버 상태. 비어 있으면 모두 조회한다.
        sort: 최신순 또는 오래된 순 정렬 기준.

    Returns:
        현재 페이지의 멤버십 이력과 전체 결과 수.
    """
    memberships = (
        Member.objects.select_related("project")
        .filter(user_id=user_id, is_leader=False)
        .exclude(project__status=Project.Status.DELETED)
    )
    if statuses:
        memberships = memberships.filter(status__in=statuses)
    order_prefix = "" if sort == "oldest" else "-"
    memberships = memberships.order_by(
        f"{order_prefix}created_at",
        f"{order_prefix}pk",
    )
    count = memberships.count()
    return list(memberships[start : start + limit]), count


def list_project_members(
    *,
    project_id: int,
    manage: bool,
    status: str | None,
) -> list[Member]:
    """조회 조건에 맞는 프로젝트 멤버를 반환한다.

    일반 조회는 참여 중인 멤버만 반환한다. 관리 조회는 요청한 상태가 없으면
    모든 멤버십 상태를 포함한다.

    Args:
        project_id: 멤버를 조회할 프로젝트 ID.
        manage: 팀장용 관리 조회 여부.
        status: 관리 조회에 적용할 멤버 상태.

    Returns:
        조회 기준에 맞는 프로젝트 멤버 목록.
    """
    effective_status = status if manage else Member.Status.JOINED
    members = Member.objects.filter(project_id=project_id).select_related(
        "user"
    )
    if effective_status is not None:
        members = members.filter(status=effective_status)
    return list(members.order_by("-is_leader", "-created_at", "-pk"))
