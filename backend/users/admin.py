from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, UserActivity


@admin.register(User)
class CustomUserAdmin(UserAdmin):
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
