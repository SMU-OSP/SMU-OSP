from django.urls import path

from .views import TeamDetail, Teams


urlpatterns = [
    path("", Teams.as_view()),
    path("<int:pk>", TeamDetail.as_view()),
]
