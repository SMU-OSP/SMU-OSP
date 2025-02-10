import requests

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.exceptions import ParseError, NotFound
from rest_framework.permissions import IsAuthenticated

from .models import User
from .serializers import (
    PrivateUserSerializer,
    PublicUserSerializer,
)


class MyInfo(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        serializer = PrivateUserSerializer(user)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def put(self, request):
        user = request.user
        serializer = PrivateUserSerializer(
            user,
            data=request.data,
            partial=True,
        )
        if serializer.is_valid():
            user = serializer.save()
            serializer = PrivateUserSerializer(user)
            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )
        else:
            return Response(serializer.errors)

    def delete(self, request):
        user = request.user

        user.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


class Users(APIView):

    def get(self, request):
        sort_by = request.query_params.get("sort_by")
        valid_sort_fields = ["commit", "star", "pr", "issue", "score"]

        if not sort_by:
            all_users = (
                User.objects.all().filter(is_superuser=False).order_by("-date_joined")
            )
        elif sort_by in valid_sort_fields:
            all_users = (
                User.objects.all().filter(is_superuser=False).order_by(f"-{sort_by}")
            )
        else:
            return Response(
                {"error": "Invalid sort field"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start = int(request.query_params.get("start", 0))
            limit = request.query_params.get("limit")
            if limit is not None:
                limit = int(limit)
        except ValueError:
            return Response(
                {"error": "Invalid pagination parameters"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if start < 0 or (limit is not None and limit <= 0):
            return Response(
                {"error": "Invalid pagination parameters"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if limit is not None:
            all_users = all_users[start : start + limit]
        else:
            all_users = all_users[start:]

        serializer = PublicUserSerializer(
            all_users,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        password = request.data.get("password")
        if not password:
            raise ParseError
        serializer = PrivateUserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            user.set_password(password)
            user.save()
            serializer = PrivateUserSerializer(user)
            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )
        else:
            return Response(serializer.errors)


class PublicUser(APIView):

    def get(self, request, username):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise NotFound
        serializer = PublicUserSerializer(user)
        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class LogIn(APIView):
    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        if not username or not password:
            raise ParseError
        user = authenticate(
            request,
            username=username,
            password=password,
        )
        if user:
            login(request, user)
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class LogOut(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_200_OK)


class GithubLogIn(APIView):

    def post(self, request):
        try:
            code = request.data.get("code")
            access_token = requests.post(
                f"https://github.com/login/oauth/access_token?code={code}&client_id={settings.GH_CLIENT_ID}&client_secret={settings.GH_CLIENT_SECRET}",
                headers={"Accept": "application/json"},
            )
            access_token = access_token.json().get("access_token")

            user_data = requests.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            user_data = user_data.json()
            user_emails = requests.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            user_emails = user_emails.json()

            try:
                user = User.objects.get(username=user_data.get("login"))
                login(request, user)
                return Response(status=status.HTTP_200_OK)
            except User.DoesNotExist:
                print("User does not exist")
                user = User.objects.create(
                    username=user_data.get("login"),
                    github_email=user_emails[0].get("email"),
                )
                user.set_unusable_password()
                user.save()
                print("User created")
                login(request, user)
                return Response(status=status.HTTP_200_OK)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)
