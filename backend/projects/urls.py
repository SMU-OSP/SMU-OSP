from django.urls import path

from .views import ProjectDetail, ProjectFilterOptions, Projects


urlpatterns = [
    path("", Projects.as_view()),
    path("options", ProjectFilterOptions.as_view()),
    path("<int:pk>", ProjectDetail.as_view()),
]
