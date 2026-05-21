from django.contrib import admin
from .models import Post, Tag


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):

    list_display = (
        "pk",
        "title",
        "author",
        "category",
        "like_count",
        "created_at",
        "updated_at",
    )
    list_filter = ("category", "on_carousel")
    search_fields = ("title", "content", "author__username")
    filter_horizontal = ("tags", "likes")

    def like_count(self, obj):
        return obj.likes.count()


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("pk", "name", "created_at")
    search_fields = ("name",)
