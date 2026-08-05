from django.db.models import Exists, OuterRef, Prefetch, Q, QuerySet

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
            has_matching_filtered_project_language=Exists(project_language_matches)
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


def list_memberships_for_user(*, user_id: int) -> QuerySet[Member]:
    return (
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
) -> QuerySet[Member]:
    members = Member.objects.filter(project_id=project_id).select_related("user")
    if not manage:
        members = members.filter(status=Member.Status.JOINED)
    return members.order_by("-is_leader", "-created_at", "-pk")
