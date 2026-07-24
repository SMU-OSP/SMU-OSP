from urllib.parse import urlparse

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Prefetch
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.responses import fail, success
from .models import Member, Project, Repository
from .serializers import (
    ProjectCreateSerializer,
    ProjectDetailSerializer,
    ProjectMemberDescriptionSerializer,
    ProjectMembershipHistorySerializer,
    ProjectMemberSerializer,
    ProjectMemberUpdateSerializer,
    ProjectSerializer,
    ProjectUpdateSerializer,
)

DEFAULT_PAGE_SIZE = 10
TRUE_QUERY_VALUES = {"1", "true"}
FALSE_QUERY_VALUES = {"0", "false"}


def parse_repository_identity(repository_url):
    parsed = urlparse(repository_url)
    path_parts = [part for part in parsed.path.split("/") if part]
    repository_name = (
        path_parts[-1].removesuffix(".git")
        if path_parts
        else parsed.hostname or "repository"
    )
    full_name = (
        "/".join(path_parts[-2:]).removesuffix(".git")
        if len(path_parts) >= 2
        else repository_name
    )
    return repository_name[:150], full_name[:300]


def parse_pagination(query_params):
    try:
        start = int(query_params.get("start", 0))
        limit = int(query_params.get("limit", DEFAULT_PAGE_SIZE))
        if start < 0 or limit <= 0:
            raise ValueError
    except ValueError:
        raise ValueError(
            "INVALID_PAGINATION_PARAMETER",
            "start는 0 이상, limit은 1 이상이어야 합니다.",
        ) from None

    return start, limit


def pagination_detail(start, limit, count):
    total_pages = (count + limit - 1) // limit if count else 1
    current_page = (start // limit) + 1

    return {
        "pagination": {
            "start": start,
            "limit": limit,
            "count": count,
            "currentPage": current_page,
            "totalPages": total_pages,
            "hasPrevious": start > 0,
            "hasNext": start + limit < count,
        }
    }


def parse_boolean_filter(query_params, name):
    value = query_params.get(name)
    if value is None:
        return False

    normalized = value.strip().lower()
    if normalized in TRUE_QUERY_VALUES:
        return True
    if normalized in FALSE_QUERY_VALUES:
        return False

    raise ValueError(
        "INVALID_PROJECT_FILTER",
        f"{name}는 true 또는 false여야 합니다.",
    )


class Projects(APIView):
    def get(self, request):
        try:
            start, limit = parse_pagination(request.query_params)
            joined = parse_boolean_filter(request.query_params, "joined")
            owned = parse_boolean_filter(request.query_params, "owned")
        except ValueError as error:
            error_code, message = error.args
            return Response(
                fail(
                    error_code,
                    message,
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (joined or owned) and not request.user.is_authenticated:
            return Response(
                fail(
                    "PERMISSION_DENIED",
                    "로그인이 필요합니다.",
                    status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        projects = (
            Project.objects.select_related("repository")
            .all()
            .order_by("-updated_at", "-pk")
        )

        if joined or owned:
            projects = projects.filter(
                members__user=request.user,
                members__status=Member.Status.JOINED,
                members__is_leader=owned,
            ).distinct()

        if request.user.is_authenticated:
            projects = projects.prefetch_related(
                Prefetch(
                    "members",
                    queryset=Member.objects.filter(
                        user=request.user,
                        status=Member.Status.JOINED,
                    ).order_by("-is_leader"),
                    to_attr="request_user_memberships",
                )
            )

        count = projects.count()
        projects = projects[start : start + limit]
        serializer = ProjectSerializer(
            projects,
            many=True,
        )
        return Response(
            success(serializer.data, pagination_detail(start, limit, count)),
            status=status.HTTP_200_OK,
        )

    def post(self, request):
        if not request.user.is_authenticated:
            return Response(
                fail(
                    "PERMISSION_DENIED",
                    "로그인이 필요합니다.",
                    status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ProjectCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                fail(
                    "INVALID_PROJECT_INPUT",
                    first_serializer_error(serializer.errors),
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        repository_url = data.get("repository_url")

        try:
            with transaction.atomic():
                project = Project.objects.create(
                    name=data["name"],
                    description=data["description"],
                    demo_url=data.get("demo_url"),
                    presentation_url=data.get("presentation_url"),
                    tech_stack=data.get("tech_stack", []),
                    used_open_source=data.get("used_open_source", []),
                )
                leader_member = Member.objects.create(
                    project=project,
                    user=request.user,
                    is_leader=True,
                    status=Member.Status.JOINED,
                )
                project.request_user_memberships = [leader_member]
                if repository_url:
                    repository_name, full_name = parse_repository_identity(
                        repository_url
                    )
                    Repository.objects.create(
                        project=project,
                        name=repository_name,
                        full_name=full_name,
                        html_url=repository_url,
                    )
        except IntegrityError:
            return Response(
                fail(
                    "INVALID_PROJECT_INPUT",
                    "이미 등록된 프로젝트명입니다.",
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            success(ProjectSerializer(project).data),
            status=status.HTTP_201_CREATED,
        )


class ProjectDetail(APIView):
    def get(self, request, pk):
        joined_members = (
            Member.objects.filter(status=Member.Status.JOINED)
            .select_related("user")
            .order_by("-is_leader", "created_at", "pk")
        )
        try:
            project = (
                Project.objects.select_related("repository")
                .prefetch_related(
                    Prefetch(
                        "members",
                        queryset=joined_members,
                        to_attr="joined_members",
                    )
                )
                .get(pk=pk)
            )
        except Project.DoesNotExist:
            return Response(
                fail(
                    "PROJECT_NOT_FOUND",
                    f"id={pk}에 해당하는 프로젝트를 찾을 수 없습니다.",
                    status.HTTP_404_NOT_FOUND,
                ),
                status=status.HTTP_404_NOT_FOUND,
            )

        current_member = next(
            (
                member
                for member in project.joined_members
                if request.user.is_authenticated
                and member.user_id == request.user.pk
            ),
            None,
        )
        can_view_members = current_member is not None
        can_edit = can_view_members and current_member.is_leader
        project.request_user_memberships = (
            [current_member] if current_member is not None else []
        )
        serializer = ProjectDetailSerializer(
            project,
            context={
                "can_view_members": can_view_members,
                "can_edit": can_edit,
            },
        )
        return Response(success(serializer.data), status=status.HTTP_200_OK)

    def put(self, request, pk):
        leader_members = Member.objects.filter(
            project=OuterRef("pk"),
            user_id=request.user.pk if request.user.is_authenticated else -1,
            status=Member.Status.JOINED,
            is_leader=True,
        )
        try:
            project = (
                Project.objects.select_related("repository")
                .annotate(is_leader=Exists(leader_members))
                .get(pk=pk)
            )
        except Project.DoesNotExist:
            return Response(
                fail(
                    "PROJECT_NOT_FOUND",
                    f"id={pk}에 해당하는 프로젝트를 찾을 수 없습니다.",
                    status.HTTP_404_NOT_FOUND,
                ),
                status=status.HTTP_404_NOT_FOUND,
            )

        if not project.is_leader:
            return Response(
                fail(
                    "PERMISSION_DENIED",
                    "프로젝트 팀장만 수정할 수 있습니다.",
                    status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ProjectUpdateSerializer(
            project,
            data=request.data,
        )
        if not serializer.is_valid():
            return Response(
                fail(
                    "INVALID_PROJECT_INPUT",
                    first_serializer_error(serializer.errors),
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        try:
            with transaction.atomic():
                for field in (
                    "name",
                    "description",
                    "demo_url",
                    "presentation_url",
                    "tech_stack",
                    "used_open_source",
                ):
                    setattr(project, field, data[field])
                project.set_status(data["status"])
                project.save()
                update_project_repository(project, data.get("repository_url"))
        except ValueError as error:
            return Response(
                fail(
                    "INVALID_PROJECT_INPUT",
                    str(error),
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except IntegrityError:
            return Response(
                fail(
                    "INVALID_PROJECT_INPUT",
                    "프로젝트 정보를 수정하지 못했습니다.",
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            success(None),
            status=status.HTTP_200_OK,
        )


class ProjectMemberships(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response(
                fail(
                    "PERMISSION_DENIED",
                    "로그인이 필요합니다.",
                    status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        memberships = (
            Member.objects.select_related("project")
            .filter(user=request.user, is_leader=False)
            .order_by("-created_at", "-pk")
        )
        serializer = ProjectMembershipHistorySerializer(memberships, many=True)
        return Response(success(serializer.data), status=status.HTTP_200_OK)


class ProjectMembers(APIView):
    def get(self, request, pk):
        if not request.user.is_authenticated:
            return Response(
                fail(
                    "PERMISSION_DENIED",
                    "로그인이 필요합니다.",
                    status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            manage = parse_boolean_filter(request.query_params, "manage")
        except ValueError:
            return Response(
                fail(
                    "INVALID_MEMBER_FILTER",
                    "manage는 true 또는 false여야 합니다.",
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        requester = (
            Member.objects.filter(
                project_id=pk,
                user=request.user,
                status=Member.Status.JOINED,
            )
            .order_by("-is_leader", "-created_at", "-pk")
            .first()
        )
        if not requester or (manage and not requester.is_leader):
            return Response(
                fail(
                    "PERMISSION_DENIED",
                    "프로젝트 멤버 조회 권한이 없습니다.",
                    status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        members = Member.objects.filter(project_id=pk).select_related("user")
        if not manage:
            members = members.filter(status=Member.Status.JOINED)
        members = members.order_by("-is_leader", "-created_at", "-pk")
        return Response(
            success(ProjectMemberSerializer(members, many=True).data),
            status=status.HTTP_200_OK,
        )

    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response(
                fail(
                    "PERMISSION_DENIED",
                    "로그인이 필요합니다.",
                    status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            project = Project.objects.get(pk=pk)
        except Project.DoesNotExist:
            return Response(
                fail(
                    "PROJECT_NOT_FOUND",
                    f"id={pk}에 해당하는 프로젝트를 찾을 수 없습니다.",
                    status.HTTP_404_NOT_FOUND,
                ),
                status=status.HTTP_404_NOT_FOUND,
            )

        memberships = list(
            Member.objects.filter(
                project=project,
                user=request.user,
            ).order_by("-created_at", "-pk")
        )
        try:
            project.validate_membership_application(memberships)
        except ValidationError as error:
            return Response(
                fail(
                    str(error.code).upper(),
                    error.message,
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        Member.objects.create(
            project=project,
            user=request.user,
            status=Member.Status.PENDING,
        )
        return Response(
            success(None),
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, pk):
        if not request.user.is_authenticated:
            return Response(
                fail(
                    "PERMISSION_DENIED",
                    "로그인이 필요합니다.",
                    status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        if not Project.objects.filter(pk=pk).exists():
            return Response(
                fail(
                    "PROJECT_NOT_FOUND",
                    f"id={pk}에 해당하는 프로젝트를 찾을 수 없습니다.",
                    status.HTTP_404_NOT_FOUND,
                ),
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = ProjectMemberDescriptionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                fail(
                    "INVALID_MEMBER_INPUT",
                    first_serializer_error(serializer.errors),
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            membership = (
                Member.objects.select_for_update()
                .filter(project_id=pk, user=request.user)
                .order_by("-is_leader", "-created_at", "-pk")
                .first()
            )

            if membership is None:
                return Response(
                    fail(
                        "MEMBERSHIP_NOT_FOUND",
                        "해당 프로젝트의 참여 또는 신청 내역을 찾을 수 없습니다.",
                        status.HTTP_404_NOT_FOUND,
                    ),
                    status=status.HTTP_404_NOT_FOUND,
                )

            try:
                membership.transition_to()
            except ValidationError as error:
                response_status = (
                    "PERMISSION_DENIED"
                    if error.code == "leader_protected"
                    else "INVALID_MEMBER_STATUS"
                )
                return Response(
                    fail(
                        response_status,
                        error.message,
                        status.HTTP_403_FORBIDDEN
                        if response_status == "PERMISSION_DENIED"
                        else status.HTTP_400_BAD_REQUEST,
                    ),
                    status=status.HTTP_403_FORBIDDEN
                    if response_status == "PERMISSION_DENIED"
                    else status.HTTP_400_BAD_REQUEST,
                )
            membership.save(update_fields=("status", "updated_at"))

            if "description" in serializer.validated_data:
                membership.description = serializer.validated_data["description"]
                membership.save(update_fields=("description", "updated_at"))
        return Response(success(None), status=status.HTTP_200_OK)


class ProjectMemberDetail(APIView):
    def put(self, request, pk, member_id):
        if not request.user.is_authenticated:
            return Response(
                fail(
                    "PERMISSION_DENIED",
                    "로그인이 필요합니다.",
                    status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        leader_exists = Member.objects.filter(
            project_id=pk,
            user=request.user,
            is_leader=True,
            status=Member.Status.JOINED,
        ).exists()
        if not leader_exists:
            return Response(
                fail(
                    "PERMISSION_DENIED",
                    "프로젝트 리더만 멤버 상태를 변경할 수 있습니다.",
                    status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ProjectMemberUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                fail(
                    "INVALID_MEMBER_INPUT",
                    first_serializer_error(serializer.errors),
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        next_status = serializer.validated_data["status"]
        try:
            with transaction.atomic():
                member = (
                    Member.objects.select_for_update()
                    .select_related("user")
                    .get(project_id=pk, pk=member_id, is_leader=False)
                )
                member.transition_to(next_status)

                update_fields = ["status", "updated_at"]
                if "description" in serializer.validated_data:
                    member.description = serializer.validated_data["description"]
                    update_fields.append("description")
                member.save(update_fields=update_fields)
        except Member.DoesNotExist:
            return Response(
                fail(
                    "MEMBER_NOT_FOUND",
                    "해당 프로젝트의 멤버를 찾을 수 없습니다.",
                    status.HTTP_404_NOT_FOUND,
                ),
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValidationError as error:
            return Response(
                fail(
                    "INVALID_MEMBER_STATUS",
                    error.message,
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(success(None), status=status.HTTP_200_OK)


def update_project_repository(project, repository_url):
    repository = getattr(project, "repository", None)

    if not repository_url:
        if repository:
            repository.delete()
        return

    if repository and repository.html_url == repository_url:
        return

    repository_name, full_name = parse_repository_identity(repository_url)
    if not repository:
        Repository.objects.create(
            project=project,
            name=repository_name,
            full_name=full_name,
            html_url=repository_url,
        )
        return

    repository.github_id = None
    repository.name = repository_name
    repository.full_name = full_name
    repository.description = None
    repository.stars = 0
    repository.forks = 0
    repository.language = None
    repository.topics = []
    repository.html_url = repository_url
    repository.github_updated_at = None
    repository.fetched_at = None
    repository.refresh_status = None
    repository.last_error_code = None
    repository.save()


def first_serializer_error(errors):
    if isinstance(errors, dict):
        first_value = next(iter(errors.values()), None)
        if isinstance(first_value, list) and first_value:
            return str(first_value[0])
        if isinstance(first_value, dict):
            return first_serializer_error(first_value)
        if first_value:
            return str(first_value)

    return "입력값을 확인해주세요."
