from django.urls import path

from .views import TrendingRepositories

urlpatterns = [
    path("repositories", TrendingRepositories.as_view()),
]
