from rest_framework.serializers import ModelSerializer
from .models import User


class JoinedUserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = (
            "username",
            "date_joined",
        )


class PublicUserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = (
            "username",
            "name",
            "major",
            "github_id",
            "github_email",
        )


class PrivateUserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = (
            "username",
            "name",
            "student_id",
            "major",
            "github_id",
            "github_email",
        )
