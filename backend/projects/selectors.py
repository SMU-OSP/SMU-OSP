from django.db.models import Exists, OuterRef, Prefetch, Q

from .forms import ProjectListQuery
from .models import (
    Member,
    Project,
    ProjectLanguage,
    RepositoryLanguage,
    RepositorySnapshot,
)


def list_projects(
    *,
    query: ProjectListQuery,
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

    if query.joined or query.owned:
        membership_filter = Q(
            members__user_id=user_id,
            members__status=Member.Status.JOINED,
        )
        if query.joined != query.owned:
            membership_filter &= Q(members__is_leader=query.owned)
        projects = projects.filter(membership_filter).distinct()

    if not query.status:
        projects = projects.exclude(status=Project.Status.FINISHED)
    if query.keyword:
        projects = projects.filter(
            Q(name__icontains=query.keyword)
            | Q(description__icontains=query.keyword)
        )
    if query.languages:
        language_filter = Q()
        for language in query.languages:
            language_filter |= Q(name__iexact=language)
        project_language_matches = ProjectLanguage.objects.filter(
            projects=OuterRef("pk")
        ).filter(language_filter)
        projects = projects.annotate(
            has_matching_filtered_project_language=Exists(project_language_matches)
        ).filter(has_matching_filtered_project_language=True)
    if query.status:
        projects = projects.filter(status=query.status)
    if query.sort == "name":
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
    projects = list(projects[query.start : query.start + query.limit])
    return projects, count
