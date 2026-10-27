from rest_framework import serializers


class TrendingRepositorySerializer(serializers.Serializer):
    """트렌딩 Repository를 메인 카드 응답으로 변환한다."""

    githubId = serializers.IntegerField(source="github_id")
    fullName = serializers.CharField(source="full_name")
    htmlUrl = serializers.URLField(source="html_url")
    description = serializers.CharField(allow_null=True)
    language = serializers.CharField()
    stars = serializers.IntegerField()
    forks = serializers.IntegerField()
