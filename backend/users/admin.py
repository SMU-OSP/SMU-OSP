from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserActivity

from import_export import resources
from import_export.admin import ExportMixin
import tablib


class UserResource(resources.ModelResource):
    class Meta:
        model = User
        fields = (
            "username",
            "score",
            "commits",
            "stars",
            "prs",
            "issues",
            "github_email",
            "name",
            "student_id",
            "major",
        )

    def export(self, *args, queryset=None, **kwargs):
        dataset = super().export(*args, queryset=queryset, **kwargs)

        csv_data = dataset.export("csv")

        bom = "\ufeff"  # UTF-8 BOM for Excel
        csv_data = bom + csv_data

        bom_dataset = tablib.Dataset()
        bom_dataset.csv = csv_data

        return bom_dataset


@admin.register(User)
class CustomUserAdmin(ExportMixin, UserAdmin):
    resource_class = UserResource
    fieldsets = (
        (
            "Profile",
            {
                "fields": (
                    "username",
                    "password",
                    "name",
                    "student_id",
                    "github_email",
                    "major",
                ),
            },
        ),
        (
            "Activity",
            {
                "fields": (
                    "score",
                    "commits",
                    "stars",
                    "prs",
                    "issues",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Important dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                ),
            },
        ),
    )

    list_display = (
        "username",
        "score",
        "commits",
        "stars",
        "prs",
        "issues",
        "github_email",
        "name",
        "student_id",
        "major",
    )


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "activity_date",
        "commits",
        "prs",
        "issues",
    )
    search_fields = ("user",)
    list_filter = ("activity_date",)
