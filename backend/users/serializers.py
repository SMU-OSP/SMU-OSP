from rest_framework.serializers import ModelSerializer

from .models import User


class PublicUserSerializer(ModelSerializer):
    """공개 사용자 목록에 노출할 사용자 정보를 변환한다."""

    class Meta:
        model = User
        fields = (
            "username",
            "date_joined",
            "score",
            "commits",
            "stars",
            "prs",
            "issues",
        )


class PublicUserProfileSerializer(PublicUserSerializer):
    """공개 사용자 프로필을 6개월 랭킹 지표로 변환한다."""

    def to_representation(self, instance):
        """기존 공개 응답 키에 6개월 랭킹 지표를 채운다."""
        representation = super().to_representation(instance)
        ranking = getattr(instance, "six_month_ranking", None)
        representation.update(
            score=getattr(ranking, "total_score", 0),
            commits=getattr(ranking, "commits", 0),
            stars=getattr(ranking, "stars", 0),
            prs=getattr(ranking, "pull_requests", 0),
            issues=getattr(ranking, "issues", 0),
        )
        return representation


class PrivateUserSerializer(ModelSerializer):
    """인증 사용자 본인에게 노출할 사용자 정보를 변환한다."""

    class Meta:
        model = User
        fields = (
            "username",
            "github_email",
            "name",
            "student_id",
            "major",
        )
