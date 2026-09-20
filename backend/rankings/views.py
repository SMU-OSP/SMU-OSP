from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import pagination_detail
from common.responses import fail, success
from users.services import (
    list_saved_user_rankings,
    list_six_month_user_rankings,
)

from .forms import RankingQueryForm
from .selectors import (
    list_project_rankings,
    list_six_month_project_rankings,
)
from .serializers import (
    ProjectRankingResultSerializer,
    UserRankingResultSerializer,
)


def _invalid_query_response(query_form: RankingQueryForm) -> Response:
    if "period" in query_form.errors:
        code = "INVALID_RANKING_PERIOD"
        message = "period는 6m 또는 1y여야 합니다."
    else:
        code = "INVALID_PAGINATION_PARAMETER"
        message = "start는 0 이상, limit은 1 이상 100 이하여야 합니다."
    return Response(
        fail(code, message, status.HTTP_400_BAD_REQUEST),
        status=status.HTTP_400_BAD_REQUEST,
    )


class UserRankings(APIView):
    """선택한 기간의 사용자 랭킹을 제공한다."""

    def get(self, request):
        """사용자 랭킹 목록을 반환한다."""
        query_form = RankingQueryForm(request.query_params)
        if not query_form.is_valid():
            return _invalid_query_response(query_form)
        query = query_form.to_query()
        if query.period == "1y":
            results, count = list_saved_user_rankings(
                start=query.start,
                limit=query.limit,
            )
        else:
            results, count = list_six_month_user_rankings(
                start=query.start,
                limit=query.limit,
            )
        return Response(
            success(
                UserRankingResultSerializer(results, many=True).data,
                pagination_detail(
                    query.start,
                    query.limit,
                    count,
                ),
            ),
            status=status.HTTP_200_OK,
        )


class ProjectRankings(APIView):
    """선택한 기간의 프로젝트 랭킹을 제공한다."""

    def get(self, request):
        """프로젝트 랭킹 목록을 반환한다."""
        query_form = RankingQueryForm(request.query_params)
        if not query_form.is_valid():
            return _invalid_query_response(query_form)
        query = query_form.to_query()
        if query.period == "1y":
            results, count = list_project_rankings(
                start=query.start,
                limit=query.limit,
            )
        else:
            results, count = list_six_month_project_rankings(
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
