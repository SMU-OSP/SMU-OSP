from django.contrib import admin

from .models import (
    ProjectRankingResult,
    ProjectRankingRun,
    ProjectRankingWeight,
)


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
        return not ProjectRankingWeight.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


class ProjectRankingResultInline(admin.TabularInline):
    model = ProjectRankingResult
    extra = 0
    can_delete = False
    readonly_fields = (
        "project",
        "rank",
        "total_score",
        "stars",
        "forks",
        "commits",
        "pull_requests",
        "actual_period_start",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ProjectRankingRun)
class ProjectRankingRunAdmin(admin.ModelAdmin):
    list_display = ("pk", "period_start", "period_end", "calculated_at")
    readonly_fields = (
        "period_start",
        "period_end",
        "calculated_at",
        "stars_weight",
        "forks_weight",
        "commits_weight",
        "pull_requests_weight",
    )
    inlines = (ProjectRankingResultInline,)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
