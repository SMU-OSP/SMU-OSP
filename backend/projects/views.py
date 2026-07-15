from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.responses import fail, success
from teams.models import Team

from .github import GitHubRepositoryError, upsert_repository_from_url
from .models import Project
from .serializers import (
    ProjectCreateSerializer,
    ProjectDetailSerializer,
    ProjectSerializer,
)

DEFAULT_PAGE_SIZE = 10


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
                    "REQUIRED_FIELD_MISSING",
                    first_serializer_error(serializer.errors),
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        idempotency_key = data["idempotency_key"]
        existing_project = Project.objects.select_related("repository").filter(
            idempotency_key=idempotency_key
        ).first()
        if existing_project:
            return Response(
                success(ProjectSerializer(existing_project).data),
                status=status.HTTP_200_OK,
            )

        team = Team.objects.filter(pk=data["team_id"]).first()
        if not team:
            return Response(
                fail(
                    "TEAM_NOT_FOUND",
                    "존재하지 않는 팀입니다.",
                    status.HTTP_404_NOT_FOUND,
                ),
                status=status.HTTP_404_NOT_FOUND,
            )

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

        try:
            with transaction.atomic():
                project = Project.objects.create(
                    team_id=team.pk,
                    team_name=team.name,
                    name=data["name"],
                    description=data["description"],
                    idempotency_key=idempotency_key,
                    repository=repository,
                    repository_url=repository_url,
                    demo_url=data.get("demo_url"),
                    presentation_url=data.get("presentation_url"),
                    tech_stack=data.get("tech_stack", []),
                    used_open_source=data.get("used_open_source", []),
                    visibility=data.get("visibility", Project.Visibility.PUBLIC),
                )
        except IntegrityError:
            project = Project.objects.select_related("repository").get(
                idempotency_key=idempotency_key
            )
            return Response(
                success(ProjectSerializer(project).data),
                status=status.HTTP_200_OK,
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

        team = (
            Team.objects.prefetch_related("members")
            .filter(pk=project.team_id)
            .first()
        )
        serializer = ProjectDetailSerializer(project, context={"team": team})
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

    return "필수 입력값을 확인해주세요."
