from django.db import models
from common.models import CommonModel


class Post(CommonModel):

    title = models.CharField(
        max_length=100,
        default="",
    )
    content = models.TextField()
    image = models.ImageField(
        null=True,
        blank=True,
    )
    on_carousel = models.BooleanField(
        default=False,
    )

    # def __str__(self) -> str:
    #     return self.name

    # class Meta:
    #     verbose_name_plural = "Posts"
