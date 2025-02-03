from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.exceptions import ParseError, NotFound
from rest_framework.permissions import IsAuthenticated

from .models import User
from .serializers import (
    PrivateUserSerializer,
    PublicUserSerializer,
    JoinedUserSerializer,
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
        all_users = User.objects.all().order_by("-date_joined")

        limit = request.query_params.get("limit", 5)
        if type(limit) == str:
            limit = int(limit)

        all_users = all_users[:limit]
        serializer = JoinedUserSerializer(
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


class ChangePassword(APIView):

    permission_classes = [IsAuthenticated]

    def put(self, request):
        user = request.user
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")
        if not old_password or not new_password:
            raise ParseError
        if user.check_password(old_password):
            user.set_password(new_password)
            user.save()
            return Response(status=status.HTTP_200_OK)
        else:
            raise ParseError
