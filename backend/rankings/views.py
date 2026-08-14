from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import pagination_detail
from common.responses import fail, success

from .forms import ProjectRankingQueryForm
from .selectors import list_project_rankings
from .serializers import ProjectRankingResultSerializer


class ProjectRankings(APIView):
    """마지막으로 정상 계산된 1년 프로젝트 랭킹을 제공한다."""

    def get(self, request):
        """프로젝트 랭킹 목록을 반환한다."""
        query_form = ProjectRankingQueryForm(request.query_params)
        if not query_form.is_valid():
            return Response(
                fail(
                    "INVALID_PAGINATION_PARAMETER",
                    "start는 0 이상, limit은 1 이상 100 이하여야 합니다.",
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        query = query_form.to_query()
        results, count = list_project_rankings(
            start=query.start,
            limit=query.limit,
        )
        return Response(
            success(
                ProjectRankingResultSerializer(results, many=True).data,
                pagination_detail(query.start, query.limit, count),
            ),
            status=status.HTTP_200_OK,
        )
