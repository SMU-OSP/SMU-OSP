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


class ProjectCreateSerializer(serializers.ModelSerializer):
    idempotencyKey = serializers.CharField(
        source="idempotency_key",
        max_length=100,
        write_only=True,
    )
    teamId = serializers.IntegerField(source="team_id")
    repositoryUrl = serializers.URLField(
        source="repository_url",
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    demoUrl = serializers.URLField(
        source="demo_url",
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    presentationUrl = serializers.URLField(
        source="presentation_url",
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    techStack = serializers.ListField(
        source="tech_stack",
        child=serializers.CharField(),
        required=False,
    )
    usedOpenSource = serializers.ListField(
        source="used_open_source",
        child=serializers.CharField(),
        required=False,
    )

    class Meta:
        model = Project
        fields = (
            "idempotencyKey",
            "teamId",
            "name",
            "description",
            "repositoryUrl",
            "demoUrl",
            "presentationUrl",
            "techStack",
            "usedOpenSource",
            "visibility",
        )

    def validate(self, attrs):
        attrs["idempotency_key"] = self._strip_required(
            attrs.get("idempotency_key"),
            "멱등키가 필요합니다.",
        )
        attrs["name"] = self._strip_required(
            attrs.get("name"),
            "프로젝트명을 입력해주세요.",
        )
        attrs["description"] = self._strip_required(
            attrs.get("description"),
            "프로젝트 설명을 입력해주세요.",
        )

        for field in ("repository_url", "demo_url", "presentation_url"):
            attrs[field] = self._strip_optional(attrs.get(field))

        attrs["tech_stack"] = self._normalize_string_list(
            attrs.get("tech_stack", [])
        )
        attrs["used_open_source"] = self._normalize_string_list(
            attrs.get("used_open_source", [])
        )
        return attrs

    def _strip_required(self, value, message):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError(message)
        return value

    def _strip_optional(self, value):
        value = (value or "").strip()
        return value or None

    def _normalize_string_list(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("목록 형식으로 입력해주세요.")
        return [item.strip() for item in value if item and item.strip()]


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
