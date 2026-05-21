from django.urls import path
from .views import Posts, PostDetail, PostCount, PostLike

urlpatterns = [
    path("", Posts.as_view()),
    path("count", PostCount.as_view(), name="post-count"),
    path("<int:pk>", PostDetail.as_view()),
    path("<int:pk>/like", PostLike.as_view(), name="post-like"),
]
