from django.urls import path
from .views import MyInfo, Users, PublicUser, ChangePassword


urlpatterns = [
    path("", Users.as_view()),
    path("myinfo", MyInfo.as_view()),
    path("change-password", ChangePassword.as_view()),
    path("<str:username>", PublicUser.as_view()),
]
