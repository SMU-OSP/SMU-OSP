from django.urls import path
from .views import MyInfo, LogIn, LogOut, Users, PublicUser, GithubLogIn, UserCount


urlpatterns = [
    path("", Users.as_view()),
    path("myinfo", MyInfo.as_view()),
    path("log-in", LogIn.as_view()),
    path("log-out", LogOut.as_view()),
    path("github", GithubLogIn.as_view()),
    path("@<str:username>", PublicUser.as_view()),
    path("count", UserCount.as_view(), name="post-count"),
]
