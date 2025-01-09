from django.urls import path
from .views import MyInfo, Users, PublicUser, ChangePassword, LogIn, LogOut, JWTLogIn


urlpatterns = [
    path("", Users.as_view()),
    path("myinfo", MyInfo.as_view()),
    path("change-password", ChangePassword.as_view()),
    path("log-in", LogIn.as_view()),
    path("log-out", LogOut.as_view()),
    path("jwt-login", JWTLogIn.as_view()),
    path("<str:username>", PublicUser.as_view()),
]
