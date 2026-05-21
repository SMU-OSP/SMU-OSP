from django.utils.html import linebreaks

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from .models import Post
from .serializers import PostSerializer


class Posts(APIView):

    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        all_posts = Post.objects.all().order_by("-created_at")

        if "carousel" in request.query_params:
            all_posts = all_posts.filter(on_carousel=True)

        category = request.query_params.get("category")
        if category:
            all_posts = all_posts.filter(category=category)

        tag = request.query_params.get("tag")
        if tag:
            all_posts = all_posts.filter(tags__name=tag)

        if "carousel" not in request.query_params:
            try:
                start = int(request.query_params.get("start", 0))
                limit = int(request.query_params.get("limit", 5))
            except ValueError:
                return Response(
                    {"error": "Invalid pagination parameters"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if start < 0 or limit <= 0:
                return Response(
                    {"error": "Invalid pagination parameters"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            all_posts = all_posts[start : start + limit]

        serializer = PostSerializer(
            all_posts,
            many=True,
            context={"request": request},
        )

        data = serializer.data
        for post in data:
            post["content"] = linebreaks(post["content"])

        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = PostSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        post = serializer.save(author=request.user)
        return Response(
            PostSerializer(post, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


class PostDetail(APIView):

    permission_classes = [IsAuthenticatedOrReadOnly]

    def _get_object(self, pk):
        try:
            return Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            raise NotFound

    def get(self, request, pk):
        post = self._get_object(pk)
        serializer = PostSerializer(post, context={"request": request})
        data = serializer.data
        data["content"] = linebreaks(data["content"])
        return Response(data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        post = self._get_object(pk)
        if post.author_id and post.author_id != request.user.pk:
            raise PermissionDenied
        serializer = PostSerializer(
            post,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        post = self._get_object(pk)
        if post.author_id and post.author_id != request.user.pk:
            raise PermissionDenied
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PostLike(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            raise NotFound

        if post.likes.filter(pk=request.user.pk).exists():
            post.likes.remove(request.user)
            liked = False
        else:
            post.likes.add(request.user)
            liked = True

        return Response(
            {"liked": liked, "likes_count": post.likes.count()},
            status=status.HTTP_200_OK,
        )


class PostCount(APIView):

    def get(self, request):
        post_count = Post.objects.count()
        return Response(
            post_count,
            status=status.HTTP_200_OK,
        )
