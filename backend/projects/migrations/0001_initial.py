# FEAT-001-001

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Repository",
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
                (
                    "github_id",
                    models.PositiveBigIntegerField(blank=True, null=True, unique=True),
                ),
                ("name", models.CharField(max_length=255)),
                ("full_name", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True, null=True)),
                ("stars", models.PositiveIntegerField(default=0)),
                ("forks", models.PositiveIntegerField(default=0)),
                ("language", models.CharField(blank=True, max_length=100, null=True)),
                ("topics", models.JSONField(blank=True, default=list)),
                ("html_url", models.URLField(max_length=500)),
                ("github_updated_at", models.DateTimeField(blank=True, null=True)),
                ("fetched_at", models.DateTimeField(blank=True, null=True)),
                (
                    "refresh_status",
                    models.CharField(
                        blank=True,
                        choices=[("SUCCESS", "Success"), ("FAILED", "Failed")],
                        max_length=20,
                        null=True,
                    ),
                ),
                ("last_error_code", models.CharField(blank=True, max_length=100, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Project",
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
                ("team_id", models.PositiveBigIntegerField()),
                ("team_name", models.CharField(max_length=100)),
                ("name", models.CharField(max_length=100)),
                ("description", models.TextField()),
                ("repository_url", models.URLField(blank=True, max_length=500, null=True)),
                ("demo_url", models.URLField(blank=True, max_length=500, null=True)),
                (
                    "presentation_url",
                    models.URLField(blank=True, max_length=500, null=True),
                ),
                ("tech_stack", models.JSONField(blank=True, default=list)),
                ("used_open_source", models.JSONField(blank=True, default=list)),
                (
                    "visibility",
                    models.CharField(
                        choices=[("PUBLIC", "Public"), ("PRIVATE", "Private")],
                        default="PUBLIC",
                        max_length=20,
                    ),
                ),
                (
                    "repository",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="project",
                        to="projects.repository",
                    ),
                ),
            ],
        ),
    ]
