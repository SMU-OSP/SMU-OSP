from django.contrib import admin

from .models import Team, TeamMember


class TeamMemberInline(admin.TabularInline):
    model = TeamMember
    extra = 0


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("pk", "name", "leader_name", "created_at", "updated_at")
    search_fields = ("name", "description", "leader_name")
    inlines = (TeamMemberInline,)


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("pk", "team", "name", "role", "status", "joined_at")
    search_fields = ("name", "role", "github_id", "email")
    list_filter = ("status",)
