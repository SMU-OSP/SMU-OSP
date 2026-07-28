from django.urls import path

from .views import (
    ProjectDetail,
    ProjectMemberDetail,
    ProjectMembers,
    ProjectMemberships,
    ProjectRepositoryRefresh,
    Projects,
)


urlpatterns = [
    path("", Projects.as_view()),
    path("members", ProjectMemberships.as_view()),
    path("<int:pk>/members", ProjectMembers.as_view()),
    path("<int:pk>/members/<int:member_id>", ProjectMemberDetail.as_view()),
    path(
        "<int:pk>/repository/refresh",
        ProjectRepositoryRefresh.as_view(),
    ),
    path("<int:pk>", ProjectDetail.as_view()),
]
