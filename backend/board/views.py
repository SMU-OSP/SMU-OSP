from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAdminUser

from .models import Post
from .serializers import PostSerializer


class Board(APIView):

    # def get_permissions(self):
    #     if self.request.method == "POST":
    #         return [IsAdminUser()]
    #     return super().get_permissions()

    def get(self, request):
        all_posts = Post.objects.all().order_by("-created_at")

        if "carousel" in request.query_params:
            all_posts = all_posts.filter(on_carousel=True)
        else:
            limit = request.query_params.get("limit", 5)
            if type(limit) == str:
                limit = int(limit)

            all_posts = all_posts[:limit]

        serializer = PostSerializer(
            all_posts,
            many=True,
        )
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class PostDetail(APIView):

    def get(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            raise NotFound
        serializer = PostSerializer(post)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
