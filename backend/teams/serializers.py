from django.db import transaction
from rest_framework import serializers

from .models import Team, TeamMember


class TeamMemberSerializer(serializers.ModelSerializer):
    teamId = serializers.IntegerField(source="team_id", read_only=True)
    userId = serializers.IntegerField(source="user_id", read_only=True, allow_null=True)
    githubId = serializers.CharField(
        source="github_id",
        allow_blank=True,
        allow_null=True,
        required=False,
    )
    email = serializers.EmailField(allow_blank=True, allow_null=True, required=False)
    joinedAt = serializers.DateTimeField(source="joined_at", read_only=True)

    class Meta:
        model = TeamMember
        fields = (
            "id",
            "teamId",
            "userId",
            "name",
            "role",
            "githubId",
            "email",
            "status",
            "joinedAt",
        )


class BlankableURLField(serializers.URLField):
    def run_validation(self, data=serializers.empty):
        if data == "":
            return None
        return super().run_validation(data)

    def to_internal_value(self, data):
        if data == "":
            return None
        return super().to_internal_value(data)


class TeamSerializer(serializers.ModelSerializer):
    logoUrl = BlankableURLField(
        source="logo_url",
        allow_blank=True,
        allow_null=True,
        required=False,
    )
    leaderId = serializers.IntegerField(source="leader_id", read_only=True, allow_null=True)
    leaderName = serializers.CharField(source="leader_name", read_only=True)
    projectCount = serializers.SerializerMethodField()
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)
    members = TeamMemberSerializer(many=True)

    class Meta:
        model = Team
        fields = (
            "id",
            "name",
            "description",
            "logoUrl",
            "leaderId",
            "leaderName",
            "members",
            "projectCount",
            "createdAt",
            "updatedAt",
        )

    def get_projectCount(self, obj):
        return 0

    def validate(self, attrs):
        members = self.initial_data.get("members") or []
        valid_members = [
            member
            for member in members
            if member.get("name", "").strip() and member.get("role", "").strip()
        ]
        name = attrs.get("name", "").strip()
        if not name:
            raise serializers.ValidationError({"name": "팀명을 입력해주세요."})
        if Team.objects.filter(name=name).exists():
            raise serializers.ValidationError({"name": "이미 등록된 팀명입니다."})
        if not valid_members:
            raise serializers.ValidationError({"members": "팀원을 1명 이상 입력해주세요."})
        attrs["name"] = name
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        members_data = validated_data.pop("members", [])
        request = self.context.get("request")
        leader = request.user if request and request.user.is_authenticated else None
        valid_members = [
            member
            for member in members_data
            if member["name"].strip() and member["role"].strip()
        ]
        leader_name = valid_members[0]["name"].strip()
        team = Team.objects.create(
            **validated_data,
            leader=leader,
            leader_name=leader_name,
        )

        for member in valid_members:
            TeamMember.objects.create(
                team=team,
                name=member["name"].strip(),
                role=member["role"].strip(),
                github_id=(member.get("github_id") or "").strip() or None,
                email=(member.get("email") or "").strip() or None,
            )
        return team
