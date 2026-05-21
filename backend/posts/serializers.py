from rest_framework import serializers

from .models import Post, Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name")


class PostAuthorSerializer(serializers.Serializer):
    username = serializers.CharField(read_only=True)
    name = serializers.CharField(read_only=True)


class PostSerializer(serializers.ModelSerializer):

    author = PostAuthorSerializer(read_only=True)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=30),
        required=False,
    )
    likes_count = serializers.SerializerMethodField()
    liked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            "id",
            "title",
            "content",
            "image",
            "on_carousel",
            "category",
            "author",
            "tags",
            "likes_count",
            "liked_by_me",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "author", "created_at", "updated_at")

    def get_likes_count(self, obj) -> int:
        return obj.likes.count()

    def get_liked_by_me(self, obj) -> bool:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.likes.filter(pk=request.user.pk).exists()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["tags"] = [t.name for t in instance.tags.all()]
        return data

    def _assign_tags(self, post, tag_names):
        tag_objs = []
        for raw in tag_names:
            name = raw.strip()
            if not name:
                continue
            tag, _ = Tag.objects.get_or_create(name=name)
            tag_objs.append(tag)
        post.tags.set(tag_objs)

    def create(self, validated_data):
        tag_names = validated_data.pop("tags", [])
        post = Post.objects.create(**validated_data)
        self._assign_tags(post, tag_names)
        return post

    def update(self, instance, validated_data):
        tag_names = validated_data.pop("tags", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tag_names is not None:
            self._assign_tags(instance, tag_names)
        return instance
