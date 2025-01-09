from rest_framework.serializers import ModelSerializer
from .models import User


class PublicUserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = (
            "username",
            "github_id",
            "github_email",
            "major"
        )


class PrivateUserSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = (
            "username",
            "password",
            "github_id",
            "github_email",
            "major",
        )
