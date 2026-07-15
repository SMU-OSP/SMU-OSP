from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Team
from .serializers import TeamSerializer


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


def validation_message(errors):
    if isinstance(errors, dict):
        for messages in errors.values():
            if isinstance(messages, list) and messages:
                return str(messages[0])
            return str(messages)
    return "입력값을 확인해주세요."


class Teams(APIView):
    def get(self, request):
        teams = Team.objects.prefetch_related("members").all().order_by("-updated_at")
        serializer = TeamSerializer(teams, many=True)
        return Response(success(serializer.data), status=status.HTTP_200_OK)

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

        serializer = TeamSerializer(data=request.data, context={"request": request})
        if not serializer.is_valid():
            return Response(
                fail(
                    "REQUIRED_FIELD_MISSING",
                    validation_message(serializer.errors),
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        team = serializer.save()
        return Response(
            success(TeamSerializer(team).data),
            status=status.HTTP_201_CREATED,
        )


class TeamDetail(APIView):
    def get(self, request, pk):
        try:
            team = Team.objects.prefetch_related("members").get(pk=pk)
        except Team.DoesNotExist:
            return Response(
                fail(
                    "TEAM_NOT_FOUND",
                    f"id={pk}에 해당하는 팀을 찾을 수 없습니다.",
                    status.HTTP_404_NOT_FOUND,
                ),
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = TeamSerializer(team)
        return Response(success(serializer.data), status=status.HTTP_200_OK)
