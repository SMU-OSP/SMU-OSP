from django.urls import path

from .views import ProjectRankings, UserRankings

urlpatterns = [
    path("users", UserRankings.as_view()),
    path("projects", ProjectRankings.as_view()),
]
