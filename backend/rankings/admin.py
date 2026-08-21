import csv
from collections.abc import Sequence
from datetime import date
from typing import Any

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse

from .forms import RankingReportForm
from .models import ProjectRanking
from .services import (
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


def _csv_response(
    *,
    columns: Sequence[str],
    rows: list[list[Any]],
    filename: str,
) -> HttpResponse:
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(columns)
    writer.writerows([[_csv_safe(value) for value in row] for row in rows])
    return response


@admin.register(ProjectRanking)
class ProjectRankingAdmin(admin.ModelAdmin):
    """기간별 사용자·프로젝트 랭킹 조회와 CSV 내보내기를 제공한다."""

    change_list_template = "admin/rankings/ranking_report.html"

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
            if request.GET.get("output") == "csv":
                filename = (
                    f'ranking-{form.cleaned_data["ranking_type"]}-'
                    f'{form.cleaned_data["period_start"]}-'
                    f'{form.cleaned_data["period_end"]}.csv'
                )
                return _csv_response(
                    columns=columns,
                    rows=rows,
                    filename=filename,
                )
            export_params = request.GET.copy()
            export_params["output"] = "csv"
            export_query = export_params.urlencode()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "랭킹 조회 및 내보내기",
            "form": form,
            "columns": columns,
            "rows": rows,
            "has_report": rows is not None,
            "export_query": export_query,
            **(extra_context or {}),
        }
        return TemplateResponse(
            request,
            self.change_list_template,
            context,
        )
