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


class BlankableURLField(serializers.URLField):
    default_error_messages = {
        **serializers.URLField.default_error_messages,
        "invalid": "올바른 URL 형식으로 입력해주세요.",
    }

    def run_validation(self, data=serializers.empty):
        if data == "":
            return None
        return super().run_validation(data)

    def to_internal_value(self, data):
        if data == "":
            return None
        return super().to_internal_value(data)


class ProjectCreateSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        max_length=100,
        validators=[],
        error_messages={
            "blank": "프로젝트명을 입력해주세요.",
            "required": "프로젝트명을 입력해주세요.",
            "max_length": "프로젝트명은 100자 이하로 입력해주세요.",
        },
    )
    description = serializers.CharField(
        error_messages={
            "blank": "프로젝트 설명을 입력해주세요.",
            "required": "프로젝트 설명을 입력해주세요.",
        },
    )
    repositoryUrl = BlankableURLField(
        source="repository_url",
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    demoUrl = BlankableURLField(
        source="demo_url",
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    presentationUrl = BlankableURLField(
        source="presentation_url",
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    techStack = serializers.ListField(
        source="tech_stack",
        child=serializers.CharField(),
        required=False,
        error_messages={"not_a_list": "목록 형식으로 입력해주세요."},
    )
    usedOpenSource = serializers.ListField(
        source="used_open_source",
        child=serializers.CharField(),
        required=False,
        error_messages={"not_a_list": "목록 형식으로 입력해주세요."},
    )
    visibility = serializers.ChoiceField(
        choices=Project.Visibility.choices,
        required=False,
        error_messages={"invalid_choice": "공개 범위를 확인해주세요."},
    )

    class Meta:
        model = Project
        fields = (
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
        name = self._strip_required(
            attrs.get("name"),
            "프로젝트명을 입력해주세요.",
        )
        if Project.objects.filter(name=name).exists():
            raise serializers.ValidationError(
                {"name": "이미 등록된 프로젝트명입니다."}
            )

        attrs["name"] = name
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
