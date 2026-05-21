from rest_framework import serializers

from .models import User


class PublicUserSerializer(serializers.ModelSerializer):

    xp = serializers.FloatField(read_only=True)
    level = serializers.IntegerField(read_only=True)
    xp_to_next_level = serializers.FloatField(read_only=True)
    xp_progress_percent = serializers.FloatField(read_only=True)
    xp_at_current_level = serializers.IntegerField(read_only=True)
    xp_at_next_level = serializers.IntegerField(read_only=True)

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
            "xp",
            "level",
            "xp_to_next_level",
            "xp_progress_percent",
            "xp_at_current_level",
            "xp_at_next_level",
        )


class PrivateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "username",
            "github_email",
            "name",
            "student_id",
            "major",
        )
