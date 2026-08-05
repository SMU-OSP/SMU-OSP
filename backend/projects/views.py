from dataclasses import asdict

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from common.responses import fail, success
from .forms import ProjectListQueryForm, ProjectMemberQueryForm
from .models import (
    Member,
    Project,
    ProjectLanguage,
)
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
from .services import (
    RepositoryRegistrationError,
    prepare_project_repository_update,
    update_project_repository,
)
from .selectors import (
    get_joined_project_member,
    get_project_detail,
    list_memberships_for_user,
    list_project_members,
    list_projects,
)


def _prepare_projects_for_serialization(projects: list[Project]) -> None:
    for project in projects:
        repository = getattr(project, "repository", None)
        if repository is None:
            continue
        repository.serialized_status = getattr(repository, "status", None)
        if not hasattr(repository, "serialized_snapshots"):
            repository.serialized_snapshots = []
        if not hasattr(repository, "serialized_languages"):
            repository.serialized_languages = []


def pagination_detail(
    start: int,
    limit: int,
    count: int,
) -> dict[str, dict[str, int | bool]]:
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


class Projects(APIView):
    def get(self, request):
        query_form = ProjectListQueryForm(request.query_params)
        if not query_form.is_valid():
            query_error = query_form.api_error()
            return Response(
                fail(
                    query_error.code,
                    query_error.message,
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        query = query_form.to_query()

        if (query.joined or query.owned) and not request.user.is_authenticated:
            return Response(
                fail(
                    "PERMISSION_DENIED",
                    "로그인이 필요합니다.",
                    status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        projects, count = list_projects(
            **asdict(query),
            user_id=request.user.pk if request.user.is_authenticated else None,
        )
        _prepare_projects_for_serialization(projects)
        serializer = ProjectSerializer(
            projects,
            many=True,
        )
        return Response(
            success(
                serializer.data,
                pagination_detail(query.start, query.limit, count),
            ),
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
        languages = data.get("languages", [])

        try:
            with transaction.atomic():
                project = Project.objects.create(
                    name=data["name"],
                    description=data["description"],
                    demo_url=data.get("demo_url"),
                    presentation_url=data.get("presentation_url"),
                )
                project.languages.set(languages)
                leader_member = Member.objects.create(
                    project=project,
                    user=request.user,
                    is_leader=True,
                    status=Member.Status.JOINED,
                )
                project.request_user_memberships = [leader_member]
        except IntegrityError:
            return Response(
                fail(
                    "INVALID_PROJECT_INPUT",
                    "이미 등록된 프로젝트명입니다.",
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        detail = None
        try:
            update_project_repository(project, repository_url)
        except ValueError as error:
            detail = {
                "repositoryRegistration": {
                    "status": "FAILED",
                    "code": getattr(error, "code", "INVALID_PROJECT_INPUT"),
                    "message": str(error),
                }
            }

        _prepare_projects_for_serialization([project])
        return Response(
            success(ProjectSerializer(project).data, detail),
            status=status.HTTP_201_CREATED,
        )


class ProjectDetail(APIView):
    def get(self, request, pk):
        try:
            project = get_project_detail(pk)
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
        project.request_user_memberships = (
            [current_member] if current_member is not None else []
        )
        can_view_members = current_member is not None
        can_edit = project.can_be_edited_by(current_member)

        _prepare_projects_for_serialization([project])
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
            if not project.is_leader:
                raise PermissionDenied

            serializer = ProjectUpdateSerializer(
                project,
                data=request.data,
            )
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            repository_url = data.get("repository_url")
            languages = data["languages"]
            repository_data = prepare_project_repository_update(
                project,
                repository_url,
            )

            with transaction.atomic():
                project = (
                    Project.objects.select_for_update()
                    .select_related("repository")
                    .annotate(is_leader=Exists(leader_members))
                    .get(pk=pk)
                )

                if not project.is_leader:
                    raise PermissionDenied

                previous_project_status = project.status
                for field in (
                    "name",
                    "description",
                    "demo_url",
                    "presentation_url",
                ):
                    setattr(project, field, data[field])
                project.set_status(data["status"])
                project.save()
                project.languages.set(languages)
                update_project_repository(
                    project,
                    repository_url,
                    previous_project_status=previous_project_status,
                    repository_data=repository_data,
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
        except PermissionDenied:
            return Response(
                fail(
                    "PERMISSION_DENIED",
                    "프로젝트 팀장만 수정할 수 있습니다.",
                    status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )
        except DRFValidationError as error:
            return Response(
                fail(
                    "INVALID_PROJECT_INPUT",
                    first_serializer_error(error.detail),
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        except RepositoryRegistrationError as error:
            return Response(
                fail(
                    error.code,
                    str(error),
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
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

    def delete(self, request, pk):
        leader_members = Member.objects.filter(
            project=OuterRef("pk"),
            user_id=request.user.pk if request.user.is_authenticated else -1,
            status=Member.Status.JOINED,
            is_leader=True,
        )
        try:
            with transaction.atomic():
                project = (
                    Project.objects.select_for_update()
                    .annotate(is_leader=Exists(leader_members))
                    .get(pk=pk)
                )

                if not project.is_leader:
                    raise PermissionDenied

                project.set_status(Project.Status.DELETED)
                project.save(update_fields=("status", "updated_at"))
        except Project.DoesNotExist:
            return Response(
                fail(
                    "PROJECT_NOT_FOUND",
                    f"id={pk}에 해당하는 프로젝트를 찾을 수 없습니다.",
                    status.HTTP_404_NOT_FOUND,
                ),
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionDenied:
            return Response(
                fail(
                    "PERMISSION_DENIED",
                    "프로젝트 팀장만 삭제할 수 있습니다.",
                    status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )
        except ValueError as error:
            return Response(
                fail(
                    "INVALID_PROJECT_STATUS",
                    str(error),
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(success(None), status=status.HTTP_200_OK)


class ProjectLanguages(APIView):
    def get(self, request):
        return Response(
            success(list(ProjectLanguage.objects.values_list("name", flat=True))),
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

        memberships = list_memberships_for_user(request.user.pk)
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

        query_form = ProjectMemberQueryForm(request.query_params)
        if not query_form.is_valid():
            query_error = query_form.api_error()
            return Response(
                fail(
                    query_error.code,
                    query_error.message,
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )
        manage = query_form.to_query().manage

        requester = get_joined_project_member(
            project_id=pk,
            user_id=request.user.pk,
        )
        if requester is None or (manage and not requester.is_leader):
            return Response(
                fail(
                    "PERMISSION_DENIED",
                    "프로젝트 멤버 조회 권한이 없습니다.",
                    status.HTTP_403_FORBIDDEN,
                ),
                status=status.HTTP_403_FORBIDDEN,
            )

        members = list_project_members(
            project_id=pk,
            joined_only=not manage,
        )

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
                membership.transition_to(
                    description=serializer.validated_data.get("description"),
                    update_description="description" in serializer.validated_data,
                )
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
            membership.save(
                update_fields=("status", "description", "joined_at", "updated_at")
            )

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

        leader_members = Member.objects.filter(
            project=OuterRef("pk"),
            user=request.user,
            is_leader=True,
            status=Member.Status.JOINED,
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
                project = (
                    Project.objects.select_for_update()
                    .annotate(is_leader=Exists(leader_members))
                    .get(pk=pk)
                )
                if not project.is_leader:
                    raise ValidationError(
                        "프로젝트 리더만 멤버 상태를 변경할 수 있습니다.",
                        code="leader_required",
                    )

                member = (
                    Member.objects.select_for_update()
                    .select_related("user")
                    .get(project_id=pk, pk=member_id, is_leader=False)
                )
                member.project = project
                member.transition_to(
                    next_status,
                    description=serializer.validated_data.get("description"),
                    update_description="description" in serializer.validated_data,
                    require_description=next_status == Member.Status.LEFT,
                )
                member.save(
                    update_fields=("status", "description", "joined_at", "updated_at")
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
            response_status = {
                "leader_required": "PERMISSION_DENIED",
                "project_capacity_reached": "PROJECT_CAPACITY_REACHED",
                "member_description_required": "INVALID_MEMBER_INPUT",
            }.get(error.code, "INVALID_MEMBER_STATUS")
            response_code = (
                status.HTTP_403_FORBIDDEN
                if response_status == "PERMISSION_DENIED"
                else status.HTTP_400_BAD_REQUEST
            )
            return Response(
                fail(
                    response_status,
                    error.message,
                    response_code,
                ),
                status=response_code,
            )

        return Response(success(None), status=status.HTTP_200_OK)


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
