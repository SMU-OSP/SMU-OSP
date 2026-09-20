import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Team",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("description", models.TextField(blank=True, null=True)),
                ("logo_url", models.URLField(blank=True, max_length=500, null=True)),
                ("leader_name", models.CharField(default="", max_length=100)),
                (
                    "leader",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="leading_teams",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TeamMember",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100)),
                ("role", models.CharField(max_length=100)),
                (
                    "github_id",
                    models.CharField(blank=True, max_length=100, null=True),
                ),
                ("email", models.EmailField(blank=True, max_length=254, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("ACTIVE", "Active"), ("INACTIVE", "Inactive")],
                        default="ACTIVE",
                        max_length=30,
                    ),
                ),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                (
                    "team",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="members",
                        to="teams.team",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="team_memberships",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
