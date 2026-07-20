from urllib.parse import urlparse

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.responses import fail, success
from .models import Member, Project, Repository
from .serializers import ProjectCreateSerializer, ProjectSerializer

DEFAULT_PAGE_SIZE = 10


def parse_repository_identity(repository_url):
    parsed = urlparse(repository_url)
    path_parts = [part for part in parsed.path.split("/") if part]
    repository_name = (
        path_parts[-1].removesuffix(".git")
        if path_parts
        else parsed.hostname or "repository"
    )
    full_name = (
        "/".join(path_parts[-2:]).removesuffix(".git")
        if len(path_parts) >= 2
        else repository_name
    )
    return repository_name[:150], full_name[:300]


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

        projects = (
            Project.objects.select_related("repository")
            .all()
            .order_by("-updated_at", "-pk")
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
        repository_url = data.get("repository_url")

        try:
            with transaction.atomic():
                project = Project.objects.create(
                    name=data["name"],
                    description=data["description"],
                    demo_url=data.get("demo_url"),
                    presentation_url=data.get("presentation_url"),
                    tech_stack=data.get("tech_stack", []),
                    used_open_source=data.get("used_open_source", []),
                )
                Member.objects.create(
                    project=project,
                    user=request.user,
                    is_leader=True,
                    status=Member.Status.JOINED,
                )
                if repository_url:
                    repository_name, full_name = parse_repository_identity(
                        repository_url
                    )
                    Repository.objects.create(
                        project=project,
                        name=repository_name,
                        full_name=full_name,
                        html_url=repository_url,
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
