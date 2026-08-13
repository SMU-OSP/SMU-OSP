from django.urls import path

from .views import ProjectRankings

urlpatterns = [
    path("projects", ProjectRankings.as_view()),
]
