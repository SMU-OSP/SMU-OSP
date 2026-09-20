from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.responses import success

from .selectors import list_trending_repositories
from .serializers import TrendingRepositorySerializer


class TrendingRepositories(APIView):
    """최근 선정된 트렌딩 GitHub Repository를 제공한다."""

    def get(self, request):
        """메인 화면에 노출할 최신 Repository 목록을 반환한다."""
        repositories = list_trending_repositories()
        return Response(
            success(
                TrendingRepositorySerializer(
                    repositories,
                    many=True,
                ).data
            ),
            status=status.HTTP_200_OK,
        )
