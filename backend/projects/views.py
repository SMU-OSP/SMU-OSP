from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.responses import fail, success

from .models import Project
from .serializers import ProjectSerializer

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
