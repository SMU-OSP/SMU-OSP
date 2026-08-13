from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.responses import success

from .selectors import get_latest_project_rankings
from .serializers import ProjectRankingResultSerializer


class ProjectRankings(APIView):
    """마지막으로 정상 계산된 1년 프로젝트 랭킹을 제공한다."""

    def get(self, request):
        """프로젝트 랭킹 목록을 반환한다."""
        results = get_latest_project_rankings()
        return Response(
            success(ProjectRankingResultSerializer(results, many=True).data),
            status=status.HTTP_200_OK,
        )
