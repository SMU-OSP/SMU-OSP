from dataclasses import asdict

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from common.authentication import api_login_required
from common.pagination import pagination_detail
from common.responses import fail, success

from .forms import ProjectListQueryForm, ProjectMemberQueryForm
from .models import (
    Member,
    Project,
    ProjectLanguage,
)
from .permissions import (
    ProjectPermissionDenied,
    can_edit_project,
    require_project_access,
    require_project_leader,
)
from .selectors import (
    get_project_detail,
    list_memberships_for_user,
    list_project_members,
    list_projects,
)
from .serializers import (
    ProjectCreateSerializer,
    ProjectDetailSerializer,
    ProjectMemberDescriptionSerializer,
    ProjectMemberSerializer,
    ProjectMembershipHistorySerializer,
    ProjectMemberUpdateSerializer,
    ProjectSerializer,
    ProjectUpdateSerializer,
)
from .services import (
    ProjectCreationError,
    RepositoryRegistrationError,
    change_project_member_status,
    create_project,
    prepare_project_repository_update,
    update_project_repository,
)

PROJECT_NOT_FOUND_MESSAGE = (
    "요청한 프로젝트가 없거나 삭제되었을 수 있습니다."
)


def _project_permission_denied_response(
    error: ProjectPermissionDenied,
) -> Response:
    return Response(
        fail(
            "PERMISSION_DENIED",
            str(error),
            status.HTTP_403_FORBIDDEN,
        ),
        status=status.HTTP_403_FORBIDDEN,
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

    @api_login_required
    def post(self, request):
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
        try:
            result = create_project(
                actor=request.user,
                name=data["name"],
                description=data["description"],
                repository_url=data.get("repository_url"),
                demo_url=data.get("demo_url"),
                presentation_url=data.get("presentation_url"),
                languages=data.get("languages", []),
            )
        except ProjectCreationError as error:
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
                    "프로젝트를 생성하지 못했습니다.",
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

        project = result.project
        project.request_user_memberships = [result.leader_member]
        detail = None
        if result.repository_error is not None:
            error = result.repository_error
            detail = {
                "repositoryRegistration": {
                    "status": "FAILED",
                    "code": error.code,
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
                    PROJECT_NOT_FOUND_MESSAGE,
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
        can_edit = (
            can_edit_project(project=project, member=current_member)
            if current_member is not None
            else False
        )

        _prepare_projects_for_serialization([project])
        serializer = ProjectDetailSerializer(
            project,
            context={
                "can_view_members": can_view_members,
                "can_edit": can_edit,
            },
        )
        return Response(success(serializer.data), status=status.HTTP_200_OK)

    @api_login_required
    def put(self, request, pk):
        try:
            if not Project.objects.filter(pk=pk).exists():
                raise Project.DoesNotExist
            require_project_leader(
                project_id=pk,
                user_id=request.user.pk,
            )

            serializer = ProjectUpdateSerializer(
                data=request.data,
                context={"project_id": pk},
            )
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            repository_url = data.get("repository_url")
            languages = data["languages"]
            repository_data = prepare_project_repository_update(
                pk,
                repository_url,
            )

            with transaction.atomic():
                project = (
                    Project.objects.select_for_update()
                    .select_related("repository")
                    .get(pk=pk)
                )

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
                    PROJECT_NOT_FOUND_MESSAGE,
                    status.HTTP_404_NOT_FOUND,
                ),
                status=status.HTTP_404_NOT_FOUND,
            )
        except ProjectPermissionDenied as error:
            return _project_permission_denied_response(error)
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

    @api_login_required
    def delete(self, request, pk):
        try:
            if not Project.objects.filter(pk=pk).exists():
                raise Project.DoesNotExist
            require_project_leader(
                project_id=pk,
                user_id=request.user.pk,
            )
            with transaction.atomic():
                project = Project.objects.select_for_update().get(pk=pk)

                project.set_status(Project.Status.DELETED)
                project.save(update_fields=("status", "updated_at"))
        except Project.DoesNotExist:
            return Response(
                fail(
                    "PROJECT_NOT_FOUND",
                    PROJECT_NOT_FOUND_MESSAGE,
                    status.HTTP_404_NOT_FOUND,
                ),
                status=status.HTTP_404_NOT_FOUND,
            )
        except ProjectPermissionDenied as error:
            return _project_permission_denied_response(error)
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
    @api_login_required
    def get(self, request):
        memberships = list_memberships_for_user(request.user.pk)
        serializer = ProjectMembershipHistorySerializer(memberships, many=True)
        return Response(success(serializer.data), status=status.HTTP_200_OK)


class ProjectMembers(APIView):
    @api_login_required
    def get(self, request, pk):
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

        try:
            require_project_access(
                project_id=pk,
                user_id=request.user.pk,
                manage=manage,
            )
        except ProjectPermissionDenied as error:
            return _project_permission_denied_response(error)

        members = list_project_members(
            project_id=pk,
            joined_only=not manage,
        )

        return Response(
            success(ProjectMemberSerializer(members, many=True).data),
            status=status.HTTP_200_OK,
        )

    @api_login_required
    def post(self, request, pk):
        try:
            project = Project.objects.get(pk=pk)
        except Project.DoesNotExist:
            return Response(
                fail(
                    "PROJECT_NOT_FOUND",
                    PROJECT_NOT_FOUND_MESSAGE,
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

    @api_login_required
    def delete(self, request, pk):
        if not Project.objects.filter(pk=pk).exists():
            return Response(
                fail(
                    "PROJECT_NOT_FOUND",
                    PROJECT_NOT_FOUND_MESSAGE,
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
    @api_login_required
    def put(self, request, pk, member_id):
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

        try:
            if not Project.objects.filter(pk=pk).exists():
                raise Project.DoesNotExist
            require_project_leader(
                project_id=pk,
                user_id=request.user.pk,
            )

            change_project_member_status(
                project_id=pk,
                member_id=member_id,
                next_status=serializer.validated_data["status"],
                description=serializer.validated_data.get("description"),
                update_description="description" in serializer.validated_data,
            )
        except Project.DoesNotExist:
            return Response(
                fail(
                    "PROJECT_NOT_FOUND",
                    PROJECT_NOT_FOUND_MESSAGE,
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
        except ProjectPermissionDenied as error:
            return _project_permission_denied_response(error)
        except ValidationError as error:
            response_status = {
                "project_capacity_reached": "PROJECT_CAPACITY_REACHED",
                "member_description_required": "INVALID_MEMBER_INPUT",
            }.get(error.code, "INVALID_MEMBER_STATUS")
            return Response(
                fail(
                    response_status,
                    error.message,
                    status.HTTP_400_BAD_REQUEST,
                ),
                status=status.HTTP_400_BAD_REQUEST,
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
