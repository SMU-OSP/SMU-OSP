import re
from urllib.parse import urlparse

from rest_framework import serializers

from .models import Member, Project, Repository

ALLOWED_URL_SCHEMES = {"http", "https"}
HTML_TAG_PATTERN = re.compile(r"</?[a-zA-Z][^>]*>")
MAX_DESCRIPTION_LENGTH = 2000
MAX_URL_LENGTH = 500
MAX_LIST_ITEMS = 20
MAX_LIST_ITEM_LENGTH = 100


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
        max_length=MAX_DESCRIPTION_LENGTH,
        error_messages={
            "blank": "프로젝트 설명을 입력해주세요.",
            "required": "프로젝트 설명을 입력해주세요.",
            "max_length": "프로젝트 설명은 2000자 이하로 입력해주세요.",
        },
    )
    repositoryUrl = BlankableURLField(
        source="repository_url",
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=MAX_URL_LENGTH,
        error_messages={"max_length": "URL은 500자 이하로 입력해주세요."},
    )
    demoUrl = BlankableURLField(
        source="demo_url",
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=MAX_URL_LENGTH,
        error_messages={"max_length": "URL은 500자 이하로 입력해주세요."},
    )
    presentationUrl = BlankableURLField(
        source="presentation_url",
        required=False,
        allow_null=True,
        allow_blank=True,
        max_length=MAX_URL_LENGTH,
        error_messages={"max_length": "URL은 500자 이하로 입력해주세요."},
    )
    techStack = serializers.ListField(
        source="tech_stack",
        child=serializers.CharField(
            allow_blank=True,
            max_length=MAX_LIST_ITEM_LENGTH,
            trim_whitespace=True,
            error_messages={
                "max_length": "각 항목은 100자 이하로 입력해주세요.",
            },
        ),
        required=False,
        max_length=MAX_LIST_ITEMS,
        error_messages={
            "not_a_list": "목록 형식으로 입력해주세요.",
            "max_length": "최대 20개까지 입력할 수 있습니다.",
        },
    )
    usedOpenSource = serializers.ListField(
        source="used_open_source",
        child=serializers.CharField(
            allow_blank=True,
            max_length=MAX_LIST_ITEM_LENGTH,
            trim_whitespace=True,
            error_messages={
                "max_length": "각 항목은 100자 이하로 입력해주세요.",
            },
        ),
        required=False,
        max_length=MAX_LIST_ITEMS,
        error_messages={
            "not_a_list": "목록 형식으로 입력해주세요.",
            "max_length": "최대 20개까지 입력할 수 있습니다.",
        },
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
        )

    def validate(self, attrs):
        name = self._strip_required(
            attrs.get("name"),
            "프로젝트명을 입력해주세요.",
        )
        name = self._validate_plain_text(
            "name",
            name,
            "프로젝트명",
            allow_newlines=False,
        )
        if Project.objects.filter(name=name).exists():
            raise serializers.ValidationError(
                {"name": "이미 등록된 프로젝트명입니다."}
            )

        attrs["name"] = name
        attrs["description"] = self._validate_plain_text(
            "description",
            self._strip_required(
                attrs.get("description"),
                "프로젝트 설명을 입력해주세요.",
            ),
            "프로젝트 설명",
            allow_newlines=True,
        )

        for field in ("repository_url", "demo_url", "presentation_url"):
            attrs[field] = self._strip_optional_url(attrs.get(field))

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

    def _strip_optional_url(self, value):
        value = self._strip_optional(value)
        if not value:
            return None

        if urlparse(value).scheme.lower() not in ALLOWED_URL_SCHEMES:
            raise serializers.ValidationError(
                "URL은 http 또는 https 형식으로 입력해주세요."
            )
        return value

    def _normalize_string_list(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("목록 형식으로 입력해주세요.")

        return [
            self._validate_plain_text(
                "listItem",
                item.strip(),
                "목록 항목",
                allow_newlines=False,
            )
            for item in value
            if item and item.strip()
        ]

    def _validate_plain_text(self, field, value, label, allow_newlines):
        allowed_controls = {"\t"}
        if allow_newlines:
            allowed_controls.update({"\n", "\r"})

        has_control_character = any(
            (ord(char) < 32 or ord(char) == 127) and char not in allowed_controls
            for char in value
        )
        if has_control_character:
            raise serializers.ValidationError(
                {field: f"{label}에는 제어 문자를 입력할 수 없습니다."}
            )

        if HTML_TAG_PATTERN.search(value):
            raise serializers.ValidationError(
                {field: f"{label}에는 HTML 태그를 입력할 수 없습니다."}
            )

        return value


class ProjectSerializer(serializers.ModelSerializer):
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
    maxMembers = serializers.IntegerField(source="max_members")
    repository = RepositorySerializer(read_only=True, allow_null=True)
    createdAt = serializers.DateTimeField(source="created_at")
    updatedAt = serializers.DateTimeField(source="updated_at")

    class Meta:
        model = Project
        fields = (
            "id",
            "name",
            "description",
            "demoUrl",
            "presentationUrl",
            "techStack",
            "usedOpenSource",
            "status",
            "maxMembers",
            "repository",
            "createdAt",
            "updatedAt",
        )


class ProjectMemberSerializer(serializers.ModelSerializer):
    userId = serializers.IntegerField(source="user_id", allow_null=True)
    name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    joinedAt = serializers.DateTimeField(source="created_at")

    class Meta:
        model = Member
        fields = (
            "id",
            "userId",
            "name",
            "role",
            "status",
            "description",
            "joinedAt",
        )

    def get_name(self, obj):
        if not obj.user:
            return "탈퇴한 사용자"
        return obj.user.name or obj.user.username

    def get_role(self, obj):
        return "LEADER" if obj.is_leader else "MEMBER"


class ProjectDetailSerializer(ProjectSerializer):
    memberCount = serializers.SerializerMethodField()
    canViewMembers = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()

    class Meta(ProjectSerializer.Meta):
        fields = ProjectSerializer.Meta.fields + (
            "memberCount",
            "canViewMembers",
            "members",
        )

    def get_memberCount(self, obj):
        return len(self._joined_members(obj))

    def get_canViewMembers(self, obj):
        return bool(self.context.get("can_view_members", False))

    def get_members(self, obj):
        if not self.get_canViewMembers(obj):
            return None
        return ProjectMemberSerializer(self._joined_members(obj), many=True).data

    def _joined_members(self, obj):
        joined_members = getattr(obj, "joined_members", None)
        if joined_members is not None:
            return joined_members
        return list(
            obj.members.filter(status=Member.Status.JOINED)
            .select_related("user")
            .order_by("-is_leader", "created_at", "pk")
        )
