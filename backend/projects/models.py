from django.db import models

from common.models import CommonModel


class Repository(CommonModel):
    class RefreshStatus(models.TextChoices):
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    github_id = models.PositiveBigIntegerField(null=True, blank=True, unique=True)
    name = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    stars = models.PositiveIntegerField(default=0)
    forks = models.PositiveIntegerField(default=0)
    language = models.CharField(max_length=100, null=True, blank=True)
    topics = models.JSONField(default=list, blank=True)
    html_url = models.URLField(max_length=500)
    github_updated_at = models.DateTimeField(null=True, blank=True)
    fetched_at = models.DateTimeField(null=True, blank=True)
    refresh_status = models.CharField(
        max_length=20,
        choices=RefreshStatus.choices,
        null=True,
        blank=True,
    )
    last_error_code = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return self.full_name


class Project(CommonModel):
    class Visibility(models.TextChoices):
        PUBLIC = "PUBLIC", "Public"
        PRIVATE = "PRIVATE", "Private"

    team_id = models.PositiveBigIntegerField()
    team_name = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    description = models.TextField()
    repository = models.OneToOneField(
        Repository,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="project",
    )
    repository_url = models.URLField(max_length=500, null=True, blank=True)
    demo_url = models.URLField(max_length=500, null=True, blank=True)
    presentation_url = models.URLField(max_length=500, null=True, blank=True)
    tech_stack = models.JSONField(default=list, blank=True)
    used_open_source = models.JSONField(default=list, blank=True)
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )

    def __str__(self):
        return self.name
