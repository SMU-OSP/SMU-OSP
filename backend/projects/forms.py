from dataclasses import dataclass
from typing import Any

from django import forms

from .models import Member, Project

TRUE_QUERY_VALUES = {"1", "true"}
FALSE_QUERY_VALUES = {"0", "false"}
PROJECT_FILTER_STATUSES = {
    Project.Status.ACTIVE,
    Project.Status.INACTIVE,
    Project.Status.FINISHED,
}
PROJECT_SORTS = {"latest", "name"}


class QueryBooleanField(forms.BooleanField):
    widget = forms.TextInput

    def to_python(self, value: Any) -> bool:
        if value is None:
            return super().to_python(value)

        normalized = str(value).strip().lower()
        if normalized not in TRUE_QUERY_VALUES | FALSE_QUERY_VALUES:
            raise forms.ValidationError("invalid", code="invalid")
        return super().to_python(normalized)


class QueryIntegerField(forms.IntegerField):
    def __init__(self, *, default: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.default = default

    def to_python(self, value: Any) -> int:
        parsed = super().to_python(value)
        return self.default if parsed is None else parsed


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
    status: str | None


@dataclass(frozen=True)
class MembershipHistoryQuery:
    start: int
    limit: int
    statuses: tuple[str, ...]
    sort: str


@dataclass(frozen=True)
class QueryApiError:
    code: str
    message: str


class ApiQueryForm(forms.Form):
    api_errors: dict[str, QueryApiError] = {}
    default_api_error = QueryApiError(
        "INVALID_PROJECT_FILTER",
        "프로젝트 검색 조건을 확인해주세요.",
    )

    def api_error(self) -> QueryApiError:
        error_field = next(iter(self.errors), None)
        return self.api_errors.get(error_field, self.default_api_error)


class ProjectListQueryForm(ApiQueryForm):
    api_errors = {
        "start": QueryApiError(
            "INVALID_PAGINATION_PARAMETER",
            "start는 0 이상, limit은 1 이상 100 이하여야 합니다.",
        ),
        "limit": QueryApiError(
            "INVALID_PAGINATION_PARAMETER",
            "start는 0 이상, limit은 1 이상 100 이하여야 합니다.",
        ),
        "joined": QueryApiError(
            "INVALID_PROJECT_FILTER",
            "joined는 true 또는 false여야 합니다.",
        ),
        "owned": QueryApiError(
            "INVALID_PROJECT_FILTER",
            "owned는 true 또는 false여야 합니다.",
        ),
        "keyword": QueryApiError(
            "INVALID_PROJECT_FILTER",
            "프로젝트 검색 조건을 확인해주세요.",
        ),
        "status": QueryApiError(
            "INVALID_PROJECT_FILTER",
            "지원하지 않는 프로젝트 상태입니다.",
        ),
        "sort": QueryApiError(
            "INVALID_PROJECT_FILTER",
            "지원하지 않는 정렬 방식입니다.",
        ),
    }

    start = QueryIntegerField(default=0, required=False, min_value=0)
    limit = QueryIntegerField(
        default=12,
        required=False,
        min_value=1,
        max_value=100,
    )
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


class ProjectMemberQueryForm(ApiQueryForm):
    api_errors = {
        "manage": QueryApiError(
            "INVALID_MEMBER_FILTER",
            "manage는 true 또는 false여야 합니다.",
        ),
        "status": QueryApiError(
            "INVALID_MEMBER_FILTER",
            (
                "status는 유효한 멤버 상태이며 manage=true일 때만 "
                "사용할 수 있습니다."
            ),
        ),
    }
    default_api_error = QueryApiError(
        "INVALID_MEMBER_FILTER",
        "manage는 true 또는 false여야 합니다.",
    )

    manage = QueryBooleanField(required=False)
    status = forms.ChoiceField(
        choices=Member.Status.choices,
        required=False,
    )

    def clean(self) -> dict[str, Any]:
        cleaned_data = super().clean()
        if cleaned_data.get("status") and not cleaned_data.get("manage"):
            self.add_error(
                "status",
                forms.ValidationError("invalid", code="manage_required"),
            )
        return cleaned_data

    def to_query(self) -> ProjectMemberQuery:
        if not self.is_valid():
            raise ValueError("유효한 입력만 ProjectMemberQuery로 변환할 수 있습니다.")
        return ProjectMemberQuery(
            manage=self.cleaned_data["manage"],
            status=self.cleaned_data["status"] or None,
        )


class MembershipHistoryQueryForm(ApiQueryForm):
    api_errors = {
        "start": QueryApiError(
            "INVALID_PAGINATION_PARAMETER",
            "start는 0 이상, limit은 1 이상 100 이하여야 합니다.",
        ),
        "limit": QueryApiError(
            "INVALID_PAGINATION_PARAMETER",
            "start는 0 이상, limit은 1 이상 100 이하여야 합니다.",
        ),
        "status": QueryApiError(
            "INVALID_MEMBER_FILTER",
            "지원하지 않는 멤버 상태입니다.",
        ),
        "sort": QueryApiError(
            "INVALID_MEMBER_FILTER",
            "지원하지 않는 정렬 방식입니다.",
        ),
    }
    default_api_error = QueryApiError(
        "INVALID_MEMBER_FILTER",
        "신청 내역 조회 조건을 확인해주세요.",
    )

    start = QueryIntegerField(default=0, required=False, min_value=0)
    limit = QueryIntegerField(
        default=12,
        required=False,
        min_value=1,
        max_value=100,
    )
    status = forms.CharField(required=False, strip=True)
    sort = forms.ChoiceField(
        choices=(
            ("latest", "latest"),
            ("oldest", "oldest"),
        ),
        required=False,
    )

    def clean_status(self) -> tuple[str, ...]:
        value = self.cleaned_data["status"]
        if not value:
            return ()
        statuses = tuple(
            status.strip().upper()
            for status in value.split(",")
            if status.strip()
        )
        if not statuses or any(
            status not in Member.Status.values for status in statuses
        ):
            raise forms.ValidationError("invalid", code="invalid_status")
        return statuses

    def to_query(self) -> MembershipHistoryQuery:
        if not self.is_valid():
            raise ValueError(
                "유효한 입력만 MembershipHistoryQuery로 변환할 수 있습니다."
            )
        return MembershipHistoryQuery(
            start=self.cleaned_data["start"],
            limit=self.cleaned_data["limit"],
            statuses=self.cleaned_data["status"],
            sort=self.cleaned_data["sort"] or "latest",
        )
