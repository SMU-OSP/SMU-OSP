from django.contrib import admin

from .models import Member, Project, Repository


class MemberInline(admin.TabularInline):
    model = Member
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "name",
        "status",
        "max_members",
        "updated_at",
    )
    search_fields = (
        "name",
        "repository__full_name",
        "repository__html_url",
    )
    list_filter = ("status",)
    inlines = (MemberInline,)


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "project",
        "user",
        "is_leader",
        "status",
        "updated_at",
    )
    search_fields = ("project__name", "user__username")
    list_filter = ("is_leader", "status")


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "project",
        "github_id",
        "full_name",
    )
    search_fields = ("project__name", "name", "full_name", "html_url")
