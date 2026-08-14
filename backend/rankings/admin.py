from django.contrib import admin

from .models import ProjectRanking, ProjectRankingWeight


@admin.register(ProjectRankingWeight)
class ProjectRankingWeightAdmin(admin.ModelAdmin):
    list_display = (
        "stars",
        "forks",
        "commits",
        "pull_requests",
        "updated_at",
    )

    def has_add_permission(self, request):
        return (
            super().has_add_permission(request)
            and not ProjectRankingWeight.objects.exists()
        )

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ProjectRanking)
class ProjectRankingAdmin(admin.ModelAdmin):
    list_display = ("rank", "project", "total_score", "period_end")
    readonly_fields = (
        "project",
        "rank",
        "total_score",
        "stars",
        "forks",
        "commits",
        "pull_requests",
        "stars_weight",
        "forks_weight",
        "commits_weight",
        "pull_requests_weight",
        "period_start",
        "period_end",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
