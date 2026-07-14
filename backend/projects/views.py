from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Project
from .serializers import ProjectSerializer


def success(data):
    return {
        "status": "SUCCESS",
        "data": data,
        "detail": None,
    }


def fail(code, message, http_status):
    return {
        "status": code,
        "data": None,
        "detail": {
            "message": message,
            "httpStatus": http_status,
        },
    }


class Projects(APIView):
    def get(self, request):
        projects = (
            Project.objects.select_related("repository")
            .all()
            .order_by("-updated_at")
        )
        serializer = ProjectSerializer(projects, many=True)
        return Response(success(serializer.data), status=status.HTTP_200_OK)


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
