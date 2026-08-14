from rest_framework import serializers


class ProjectRankingResultSerializer(serializers.Serializer):
    """저장된 프로젝트 랭킹 결과를 사용자 조회 형식으로 변환한다."""

    rank = serializers.IntegerField()
    projectId = serializers.IntegerField(source="project_id")
    projectName = serializers.CharField(source="project.name")
    totalScore = serializers.DecimalField(
        source="total_score",
        max_digits=30,
        decimal_places=2,
    )
    stars = serializers.IntegerField()
    forks = serializers.IntegerField()
    commits = serializers.IntegerField()
    pullRequests = serializers.IntegerField(source="pull_requests")
