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
            "github_email",
            "username",
            "name",
            "major",
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
