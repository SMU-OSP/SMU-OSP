from django.conf import settings
from django.db import models

from common.models import CommonModel


class Tag(CommonModel):
    name = models.CharField(max_length=30, unique=True)

    def __str__(self) -> str:
        return self.name


class Post(CommonModel):

    class Category(models.TextChoices):
        NOTICE = "NOTICE", "공지"
        FREE = "FREE", "자유"
        QNA = "QNA", "질문"
        PROJECT = "PROJECT", "프로젝트"

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

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
    )
    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.NOTICE,
    )
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        related_name="posts",
    )
    likes = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="liked_posts",
    )

    def __str__(self) -> str:
        return self.title or f"Post #{self.pk}"
