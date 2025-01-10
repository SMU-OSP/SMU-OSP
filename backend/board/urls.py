from django.urls import path
from .views import Board, PostDetail

urlpatterns = [
    path("", Board.as_view()),
    path("<int:pk>", PostDetail.as_view()),
]
