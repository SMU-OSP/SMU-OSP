from collections.abc import Sequence
from datetime import date
from typing import Any

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from import_export import fields, resources
from import_export.admin import ExportMixin

from .forms import RankingReportForm
from .models import ProjectRanking
from .services import (
    UserRankingResult,
    calculate_project_rankings,
    calculate_user_rankings,
)

USER_COLUMNS = (
    "순위",
    "사용자",
    "총점",
    "Star",
    "Commit",
    "PR",
    "Issue",
    "가입일",
)
PROJECT_COLUMNS = (
    "순위",
    "프로젝트",
    "총점",
    "Star",
    "Fork",
    "Commit",
    "PR",
)


class RankingResource(resources.Resource):
    """내보내기 형식에 맞게 랭킹 문자열을 준비한다."""

    def __init__(self, **kwargs: Any):
        self.escape_spreadsheet_values = kwargs.pop(
            "escape_spreadsheet_values",
            False,
        )
        super().__init__(**kwargs)

    def export_text(self, value: str) -> str:
        if self.escape_spreadsheet_values:
            return _csv_safe(value)
        return value


class UserRankingResource(RankingResource):
    """기간별 사용자 랭킹 계산 결과를 내보낸다."""

    rank = fields.Field(attribute="rank", column_name="순위")
    username = fields.Field(attribute="user__username", column_name="사용자")
    total_score = fields.Field(attribute="total_score", column_name="총점")
    stars = fields.Field(attribute="stars", column_name="Star")
    commits = fields.Field(attribute="commits", column_name="Commit")
    pull_requests = fields.Field(
        attribute="pull_requests",
        column_name="PR",
    )
    issues = fields.Field(attribute="issues", column_name="Issue")
    date_joined = fields.Field(column_name="가입일")

    @classmethod
    def get_display_name(cls) -> str:
        return "사용자 랭킹"

    def dehydrate_username(self, result: UserRankingResult) -> str:
        return self.export_text(result.user.username)

    def dehydrate_date_joined(self, result: UserRankingResult) -> date:
        return result.user.date_joined.date()


class ProjectRankingResource(RankingResource):
    """기간별 프로젝트 랭킹 계산 결과를 내보낸다."""

    rank = fields.Field(attribute="rank", column_name="순위")
    project = fields.Field(column_name="프로젝트")
    total_score = fields.Field(attribute="total_score", column_name="총점")
    stars = fields.Field(attribute="stars", column_name="Star")
    forks = fields.Field(attribute="forks", column_name="Fork")
    commits = fields.Field(attribute="commits", column_name="Commit")
    pull_requests = fields.Field(
        attribute="pull_requests",
        column_name="PR",
    )

    @classmethod
    def get_display_name(cls) -> str:
        return "프로젝트 랭킹"

    def dehydrate_project(self, result: ProjectRanking) -> str:
        return self.export_text(result.project.name)


def _ranking_report_rows(
    ranking_type: str,
    period_start: date,
    period_end: date,
) -> tuple[Sequence[str], list[list[Any]]]:
    if ranking_type == "users":
        results = calculate_user_rankings(period_start, period_end)
        return USER_COLUMNS, [
            [
                result.rank,
                result.user.username,
                result.total_score,
                result.stars,
                result.commits,
                result.pull_requests,
                result.issues,
                result.user.date_joined.date(),
            ]
            for result in results
        ]

    results = calculate_project_rankings(
        period_start,
        period_end,
    )
    return PROJECT_COLUMNS, [
        [
            result.rank,
            result.project.name,
            result.total_score,
            result.stars,
            result.forks,
            result.commits,
            result.pull_requests,
        ]
        for result in results
    ]


def _csv_safe(value: Any) -> Any:
    """스프레드시트가 문자열 값을 수식으로 실행하지 않도록 보호한다."""
    if isinstance(value, str) and value.startswith(
        ("=", "+", "-", "@", "\t", "\r")
    ):
        return f"'{value}"
    return value


@admin.register(ProjectRanking)
class ProjectRankingAdmin(ExportMixin, admin.ModelAdmin):
    """기간별 사용자·프로젝트 랭킹 조회와 내보내기를 제공한다."""

    import_export_change_list_template = (
        "admin/rankings/ranking_report.html"
    )
    to_encoding = "utf-8-sig"

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: ProjectRanking | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: ProjectRanking | None = None,
    ) -> bool:
        return False

    def has_export_permission(self, request: HttpRequest) -> bool:
        return self.has_view_permission(request)

    def get_export_resource_classes(
        self,
        request: HttpRequest,
    ) -> list[type[resources.Resource]]:
        """조회 유형에 맞는 랭킹 내보내기 명세를 반환한다."""
        if request.GET.get("ranking_type") == "users":
            return [UserRankingResource]
        return [ProjectRankingResource]

    def get_export_queryset(self, request: HttpRequest) -> list[Any]:
        """파일 제출 시에만 검증된 기간의 랭킹을 계산한다."""
        if request.method != "POST":
            return []

        form = RankingReportForm(request.GET)
        if not form.is_valid():
            return []

        ranking_type = form.cleaned_data["ranking_type"]
        period_start = form.cleaned_data["period_start"]
        period_end = form.cleaned_data["period_end"]
        if ranking_type == "users":
            return calculate_user_rankings(period_start, period_end)
        return calculate_project_rankings(period_start, period_end)

    def get_export_resource_kwargs(
        self,
        request: HttpRequest,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """스프레드시트 형식에만 수식 실행 방어를 적용한다."""
        resource_kwargs = super().get_export_resource_kwargs(
            request,
            **kwargs,
        )
        export_form = kwargs.get("export_form")
        if export_form:
            format_index = int(export_form.cleaned_data["format"])
            file_format = self.get_export_formats()[format_index]()
            resource_kwargs["escape_spreadsheet_values"] = (
                file_format.get_extension()
                in {"csv", "tsv", "ods", "xls", "xlsx"}
            )
        return resource_kwargs

    def get_export_filename(
        self,
        request: HttpRequest,
        queryset: list[Any],
        file_format: Any,
    ) -> str:
        form = RankingReportForm(request.GET)
        if not form.is_valid():
            return super().get_export_filename(
                request,
                queryset,
                file_format,
            )
        return (
            f'ranking-{form.cleaned_data["ranking_type"]}-'
            f'{form.cleaned_data["period_start"]}-'
            f'{form.cleaned_data["period_end"]}.'
            f"{file_format.get_extension()}"
        )

    def changelist_view(
        self,
        request: HttpRequest,
        extra_context: dict[str, Any] | None = None,
    ) -> HttpResponse:
        """검증된 기간의 랭킹 표 또는 CSV 응답을 반환한다."""
        if not self.has_view_permission(request):
            raise PermissionDenied

        form = RankingReportForm(request.GET or None)
        columns = None
        rows = None
        export_query = ""
        if form.is_valid():
            columns, rows = _ranking_report_rows(
                form.cleaned_data["ranking_type"],
                form.cleaned_data["period_start"],
                form.cleaned_data["period_end"],
            )
            export_query = request.GET.urlencode()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "랭킹 조회 및 내보내기",
            "form": form,
            "columns": columns,
            "rows": rows,
            "has_report": rows is not None,
            "export_query": export_query,
            "has_export_permission": self.has_export_permission(request),
            **(extra_context or {}),
        }
        return TemplateResponse(
            request,
            self.change_list_template,
            context,
        )
