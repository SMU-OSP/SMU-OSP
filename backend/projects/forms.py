from dataclasses import dataclass
from typing import Any

from django import forms

from .models import Project


TRUE_QUERY_VALUES = {"1", "true"}
FALSE_QUERY_VALUES = {"0", "false"}
PROJECT_FILTER_STATUSES = {
    Project.Status.ACTIVE,
    Project.Status.INACTIVE,
    Project.Status.FINISHED,
}
PROJECT_SORTS = {"latest", "name"}


class QueryBooleanField(forms.Field):
    def clean(self, value: str | None) -> bool:
        if value is None:
            return False

        normalized = value.strip().lower()
        if normalized in TRUE_QUERY_VALUES:
            return True
        if normalized in FALSE_QUERY_VALUES:
            return False
        raise forms.ValidationError("invalid", code="invalid")


class QueryIntegerField(forms.Field):
    def __init__(self, *, default: int, min_value: int) -> None:
        super().__init__(required=False)
        self.default = default
        self.min_value = min_value

    def clean(self, value: str | None) -> int:
        if value is None:
            return self.default
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            raise forms.ValidationError("invalid", code="invalid") from None
        if parsed < self.min_value:
            raise forms.ValidationError("invalid", code="invalid")
        return parsed


@dataclass(frozen=True)
class ProjectListQuery:
    start: int
    limit: int
    joined: bool
    owned: bool
    keyword: str | None
    languages: tuple[str, ...]
    status: str | None
    sort: str


@dataclass(frozen=True)
class ProjectMemberQuery:
    manage: bool


class ProjectListQueryForm(forms.Form):
    start = QueryIntegerField(default=0, min_value=0)
    limit = QueryIntegerField(default=10, min_value=1)
    joined = QueryBooleanField(required=False)
    owned = QueryBooleanField(required=False)
    keyword = forms.CharField(
        required=False,
        strip=True,
        max_length=100,
        empty_value=None,
    )
    techStack = forms.CharField(required=False)
    status = forms.CharField(required=False, strip=True)
    sort = forms.CharField(required=False, strip=True)

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        languages = [
            stack.strip()
            for value in self.data.getlist("techStack")
            for stack in value.split(",")
            if stack.strip()
        ]
        if len(languages) > 20 or any(
            len(language) > 50 for language in languages
        ):
            raise forms.ValidationError("invalid", code="invalid_filter")

        project_status = cleaned_data.get("status") or None
        project_status = project_status.upper() if project_status else None
        if project_status and project_status not in PROJECT_FILTER_STATUSES:
            self.add_error(
                "status",
                forms.ValidationError("invalid", code="invalid_status"),
            )
        else:
            cleaned_data["status"] = project_status

        sort = cleaned_data.get("sort") or "latest"
        if sort not in PROJECT_SORTS:
            self.add_error(
                "sort",
                forms.ValidationError("invalid", code="invalid_sort"),
            )
        else:
            cleaned_data["sort"] = sort

        cleaned_data["languages"] = tuple(languages)
        return cleaned_data

    def api_error(self) -> tuple[str, str]:
        if "start" in self.errors or "limit" in self.errors:
            return (
                "INVALID_PAGINATION_PARAMETER",
                "start는 0 이상, limit은 1 이상이어야 합니다.",
            )
        if "joined" in self.errors:
            return (
                "INVALID_PROJECT_FILTER",
                "joined는 true 또는 false여야 합니다.",
            )
        if "owned" in self.errors:
            return (
                "INVALID_PROJECT_FILTER",
                "owned는 true 또는 false여야 합니다.",
            )
        if "keyword" in self.errors or "__all__" in self.errors:
            return (
                "INVALID_PROJECT_FILTER",
                "프로젝트 검색 조건을 확인해주세요.",
            )
        if "status" in self.errors:
            return (
                "INVALID_PROJECT_FILTER",
                "지원하지 않는 프로젝트 상태입니다.",
            )
        if "sort" in self.errors:
            return (
                "INVALID_PROJECT_FILTER",
                "지원하지 않는 정렬 방식입니다.",
            )
        return (
            "INVALID_PROJECT_FILTER",
            "프로젝트 검색 조건을 확인해주세요.",
        )

    def to_query(self) -> ProjectListQuery:
        if not self.is_valid():
            raise ValueError("유효한 입력만 ProjectListQuery로 변환할 수 있습니다.")
        return ProjectListQuery(
            start=self.cleaned_data["start"],
            limit=self.cleaned_data["limit"],
            joined=self.cleaned_data["joined"],
            owned=self.cleaned_data["owned"],
            keyword=self.cleaned_data["keyword"],
            languages=self.cleaned_data["languages"],
            status=self.cleaned_data["status"],
            sort=self.cleaned_data["sort"],
        )


class ProjectMemberQueryForm(forms.Form):
    manage = QueryBooleanField(required=False)

    def to_query(self) -> ProjectMemberQuery:
        if not self.is_valid():
            raise ValueError("유효한 입력만 ProjectMemberQuery로 변환할 수 있습니다.")
        return ProjectMemberQuery(manage=self.cleaned_data["manage"])
