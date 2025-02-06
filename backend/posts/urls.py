from django.urls import path
from .views import Posts, PostDetail, PostCount

urlpatterns = [
    path("", Posts.as_view()),
    path("<int:pk>", PostDetail.as_view()),
    path("count", PostCount.as_view(), name="post-count"),
]
