from django.db import IntegrityError, transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.responses import fail, success
from teams.models import Team

from .github import GitHubRepositoryError, upsert_repository_from_url
from .models import Project
from .serializers import ProjectCreateSerializer, ProjectSerializer

DEFAULT_PAGE_SIZE = 10
VALID_SORT_FIELDS = {"latest", "name", "stars", "githubUpdated"}


def parse_pagination(query_params):
    try:
        start = int(query_params.get("start", 0))
        limit = int(query_params.get("limit", DEFAULT_PAGE_SIZE))
    except ValueError:
        return None, None

    if start < 0 or limit <= 0:
        return None, None

    return start, limit


def pagination_detail(start, limit, count):
    total_pages = (count + limit - 1) // limit if count else 1
    current_page = (start // limit) + 1

    return {
        "pagination": {
            "start": start,
            "limit": limit,
            "count": count,
            "currentPage": current_page,
            "totalPages": total_pages,
            "hasPrevious": start > 0,
            "hasNext": start + limit < count,
        }
    }


def apply_project_filters(projects, query_params):
    keyword = query_params.get("keyword", "").strip()
    tech_stack = query_params.get("techStack", "").strip()
    language = query_params.get("language", "").strip()
    visibility = query_params.get("visibility", "").strip()
    sort = query_params.get("sort", "latest").strip() or "latest"

    if visibility and visibility != "ALL":
        valid_visibility = {choice[0] for choice in Project.Visibility.choices}
        if visibility not in valid_visibility:
            return None
        projects = projects.filter(visibility=visibility)

    if sort not in VALID_SORT_FIELDS:
        return None

    if keyword:
        projects = projects.filter(
            Q(name__icontains=keyword)
            | Q(description__icontains=keyword)
            | Q(repository__full_name__icontains=keyword)
        )
    if tech_stack:
        projects = projects.filter(tech_stack__contains=[tech_stack])
    if language:
        projects = projects.filter(repository__language=language)

    if sort == "name":
        return projects.order_by("name", "pk")
    if sort == "stars":
        return projects.order_by("-repository__stars", "-updated_at", "-pk")
    if sort == "githubUpdated":
        return projects.order_by("-repository__github_updated_at", "-updated_at", "-pk")
    return projects.order_by("-updated_at", "-pk")


def project_filter_options():
    tech_stacks = set()
    for stack in Project.objects.values_list("tech_stack", flat=True):
        if isinstance(stack, list):
            tech_stacks.update(item for item in stack if item)

    languages = (
        Project.objects.select_related("repository")
        .exclude(repository__language__isnull=True)
        .exclude(repository__language="")
        .values_list("repository__language", flat=True)
        .distinct()
    )

    return {
        "techStacks": sorted(tech_stacks),
        "languages": sorted(languages),
    }


class Projects(APIView):
    def get(self, request):
        start, limit = parse_pagination(request.query_params)
        if start is None:
            return Response(
                fail(
                    "INVALID_PAGINATION_PARAMETER",
                    "start는 0 이상, limit은 1 이상이어야 합니다.",
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        projects = apply_project_filters(
            Project.objects.select_related("repository").all(),
            request.query_params,
        )
        if projects is None:
            return Response(
                fail(
                    "INVALID_PROJECT_FILTER",
                    "프로젝트 목록 조회 조건을 확인해주세요.",
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        count = projects.count()
        projects = projects[start : start + limit]
        serializer = ProjectSerializer(projects, many=True)
        return Response(
            success(serializer.data, pagination_detail(start, limit, count)),
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        if not request.user.is_authenticated:
            return Response(
                fail(
                    "PERMISSION_DENIED",
                    "로그인이 필요합니다.",
                    status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ProjectCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                fail(
                    "INVALID_PROJECT_INPUT",
                    first_serializer_error(serializer.errors),
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        repository = None
        repository_url = data.get("repository_url")
        if repository_url:
            try:
                repository = upsert_repository_from_url(repository_url)
            except GitHubRepositoryError as exc:
                return Response(
                    fail(exc.code, exc.message, exc.http_status),
                    status=exc.http_status,
                )

        if repository and Project.objects.filter(repository=repository).exists():
            return Response(
                fail(
                    "DUPLICATE_PROJECT_REPOSITORY",
                    "이미 다른 프로젝트에 연결된 Repository입니다.",
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                team = Team.objects.create(
                    name=data["name"],
                    description=data["description"],
                    leader=request.user,
                )
                project = Project.objects.create(
                    team=team,
                    name=data["name"],
                    description=data["description"],
                    repository=repository,
                    repository_url=repository_url,
                    demo_url=data.get("demo_url"),
                    presentation_url=data.get("presentation_url"),
                    tech_stack=data.get("tech_stack", []),
                    used_open_source=data.get("used_open_source", []),
                    visibility=data.get("visibility", Project.Visibility.PUBLIC),
                )
        except IntegrityError:
            return Response(
                fail(
                    "INVALID_PROJECT_INPUT",
                    "이미 등록된 프로젝트명입니다.",
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            success(ProjectSerializer(project).data),
            status=status.HTTP_201_CREATED,
        )


class ProjectFilterOptions(APIView):
    def get(self, request):
        return Response(
            success(project_filter_options()),
            status=status.HTTP_200_OK,
        )


class ProjectDetail(APIView):
    def get(self, request, pk):
        try:
            project = Project.objects.select_related("repository").get(pk=pk)
        except Project.DoesNotExist:
            return Response(
                fail(
                    "PROJECT_NOT_FOUND",
                    f"id={pk}에 해당하는 프로젝트를 찾을 수 없습니다.",
                    status.HTTP_404_NOT_FOUND,
                ),
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProjectSerializer(project)
        return Response(success(serializer.data), status=status.HTTP_200_OK)


def first_serializer_error(errors):
    if isinstance(errors, dict):
        first_value = next(iter(errors.values()), None)
        if isinstance(first_value, list) and first_value:
            return str(first_value[0])
        if isinstance(first_value, dict):
            return first_serializer_error(first_value)
        if first_value:
            return str(first_value)

    return "입력값을 확인해주세요."
