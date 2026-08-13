from rest_framework import serializers

from .models import ProjectRankingResult


class ProjectRankingResultSerializer(serializers.ModelSerializer):
    """저장된 프로젝트 랭킹 결과를 사용자 조회 형식으로 변환한다."""

    projectId = serializers.IntegerField(source="project_id")
    projectName = serializers.CharField(source="project.name")
    totalScore = serializers.DecimalField(
        source="total_score",
        max_digits=30,
        decimal_places=2,
    )
    pullRequests = serializers.IntegerField(source="pull_requests")
    activeDays = serializers.IntegerField(source="active_days")
    maxStreak = serializers.IntegerField(source="max_streak")
    currentStreak = serializers.IntegerField(source="current_streak")

    class Meta:
        model = ProjectRankingResult
        fields = (
            "rank",
            "projectId",
            "projectName",
            "totalScore",
            "stars",
            "forks",
            "commits",
            "pullRequests",
            "activeDays",
            "maxStreak",
            "currentStreak",
        )
