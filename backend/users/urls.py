from django.urls import path
from .views import (
    MyInfo,
    LogIn,
    LogOut,
    Users,
    PublicUser,
    CheckUserExist,
    GithubRegister,
    GithubLogIn,
)


urlpatterns = [
    path("", Users.as_view()),
    path("myinfo", MyInfo.as_view()),
    path("log-in", LogIn.as_view()),
    path("log-out", LogOut.as_view()),
    path("check-user-exist", CheckUserExist.as_view()),
    path("github-log-in", GithubLogIn.as_view()),
    path("github-register", GithubRegister.as_view()),
    path("@<str:username>", PublicUser.as_view()),
]
