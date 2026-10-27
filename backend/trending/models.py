from django.db import models

from common.models import CommonModel


class TrendingRepositorySelection(CommonModel):
    """한 주의 트렌딩 Repository 수집 성공 기록."""

    week_start = models.DateField(unique=True)

    class Meta:
        ordering = ("-week_start",)


class TrendingRepository(CommonModel):
    """최근 6개월 동안 노출한 GitHub Repository."""

    selection = models.ForeignKey(
        TrendingRepositorySelection,
        on_delete=models.CASCADE,
        related_name="repositories",
    )
    github_id = models.PositiveBigIntegerField(unique=True)
    full_name = models.CharField(max_length=300)
    html_url = models.URLField(max_length=500)
    # GitHub distinguishes a missing description from an empty description.
    description = models.TextField(null=True, blank=True)  # noqa: DJ001
    language = models.CharField(max_length=100)
    stars = models.PositiveIntegerField(default=0)
    forks = models.PositiveIntegerField(default=0)
    position = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("selection", "position"),
                name="trending_selection_position_uniq",
            ),
        ]
