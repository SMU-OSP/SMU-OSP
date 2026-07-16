from django.urls import path

from .views import ProjectDetail, Projects


urlpatterns = [
    path("", Projects.as_view()),
    path("<int:pk>", ProjectDetail.as_view()),
]
