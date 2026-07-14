from rest_framework import serializers

from .models import Project, Repository


class RepositorySerializer(serializers.ModelSerializer):
    githubId = serializers.IntegerField(source="github_id", allow_null=True)
    fullName = serializers.CharField(source="full_name")
    htmlUrl = serializers.URLField(source="html_url")
    updatedAt = serializers.DateTimeField(
        source="github_updated_at",
        allow_null=True,
    )
    fetchedAt = serializers.DateTimeField(source="fetched_at", allow_null=True)
    refreshStatus = serializers.CharField(source="refresh_status", allow_null=True)
    lastErrorCode = serializers.CharField(source="last_error_code", allow_null=True)

    class Meta:
        model = Repository
        fields = (
            "id",
            "githubId",
            "name",
            "fullName",
            "description",
            "stars",
            "forks",
            "language",
            "topics",
            "htmlUrl",
            "updatedAt",
            "fetchedAt",
            "refreshStatus",
            "lastErrorCode",
        )


class ProjectSerializer(serializers.ModelSerializer):
    teamId = serializers.IntegerField(source="team_id")
    teamName = serializers.CharField(source="team_name")
    repositoryId = serializers.IntegerField(source="repository_id", allow_null=True)
    repositoryUrl = serializers.URLField(source="repository_url", allow_null=True)
    demoUrl = serializers.URLField(source="demo_url", allow_null=True)
    presentationUrl = serializers.URLField(
        source="presentation_url",
        allow_null=True,
    )
    techStack = serializers.ListField(source="tech_stack", child=serializers.CharField())
    usedOpenSource = serializers.ListField(
        source="used_open_source",
        child=serializers.CharField(),
    )
    repository = RepositorySerializer(read_only=True)
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = Project
        fields = (
            "id",
            "teamId",
            "teamName",
            "name",
            "description",
            "repositoryId",
            "repositoryUrl",
            "demoUrl",
            "presentationUrl",
            "techStack",
            "usedOpenSource",
            "visibility",
            "repository",
            "createdAt",
            "updatedAt",
        )
