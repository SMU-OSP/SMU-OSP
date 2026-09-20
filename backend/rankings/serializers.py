from rest_framework import serializers


class UserRankingResultSerializer(serializers.Serializer):
    """계산된 사용자 랭킹 결과를 사용자 조회 형식으로 변환한다."""

    rank = serializers.IntegerField()
    username = serializers.CharField(source="user.username")
    totalScore = serializers.IntegerField(source="total_score")
    stars = serializers.IntegerField()
    commits = serializers.IntegerField()
    pullRequests = serializers.IntegerField(source="pull_requests")
    issues = serializers.IntegerField()
    dateJoined = serializers.DateTimeField(source="user.date_joined")


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
