import requests
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from rest_framework import status
from rest_framework.exceptions import NotFound, ParseError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import pagination_detail
from common.responses import fail, success

from .forms import UserListQueryForm
from .models import User
from .selectors import list_public_users
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
        query_form = UserListQueryForm(request.query_params)
        if not query_form.is_valid():
            return Response(
                fail(
                    "INVALID_PAGINATION_PARAMETER",
                    "start는 0 이상, limit은 1 이상 100 이하이며 유효한 정렬 기준이어야 합니다.",
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        query = query_form.to_query()
        users, count = list_public_users(
            start=query.start,
            limit=query.limit,
            sort_by=query.sort_by,
        )
        return Response(
            success(
                PublicUserSerializer(users, many=True).data,
                pagination_detail(query.start, query.limit, count),
            ),
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

        access_token = request.data.get("access_token")

        try:
            user_data = requests.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                },
            )
            user_data = user_data.json()
            username = user_data.get("login")

            try:
                user = User.objects.get(username=username)
                login(request, user)
                return Response(status=status.HTTP_200_OK)
            except Exception:
                return Response(status=status.HTTP_400_BAD_REQUEST)

        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class GithubRegister(APIView):

    def post(self, request):

        access_token = request.data.get("access_token")

        try:
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

            username = user_data.get("login")
            github_email = user_emails[0].get("email")

            user = User.objects.create(
                username=username,
                github_email=github_email,
                name=request.data.get("name"),
                student_id=request.data.get("student_id"),
                major=request.data.get("major"),
            )
            user.set_unusable_password()
            user.save()
            return Response(status=status.HTTP_200_OK)
        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class CheckUserExist(APIView):

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

            username = user_data.get("login")
            github_email = user_emails[0].get("email")

            user = User.objects.filter(username=username).first()

            return Response(
                {
                    "username": username,
                    "github_email": github_email,
                    "access_token": access_token,
                    "registered": user is not None,
                },
                status=status.HTTP_200_OK,
            )

        except Exception:
            return Response(status=status.HTTP_400_BAD_REQUEST)
