from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


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
                    "commit",
                    "star",
                    "pr",
                    "issue",
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
        "commit",
        "star",
        "pr",
        "issue",
        "github_email",
        "name",
        "student_id",
        "major",
    )
