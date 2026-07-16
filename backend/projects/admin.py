from django.contrib import admin

from .models import Project, Repository


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "name",
        "team",
        "visibility",
        "updated_at",
    )
    search_fields = ("name", "team__name", "repository_url")
    list_filter = ("visibility",)


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = (
        "pk",
        "full_name",
        "language",
        "stars",
        "forks",
        "fetched_at",
    )
    search_fields = ("name", "full_name", "html_url")
    list_filter = ("language", "refresh_status")
