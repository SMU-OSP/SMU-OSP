from rest_framework.serializers import ModelSerializer
from .models import User


class PublicUserSerializer(ModelSerializer):
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


class PrivateUserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = (
            "username",
            "github_email",
            "name",
            "student_id",
            "major",
        )
