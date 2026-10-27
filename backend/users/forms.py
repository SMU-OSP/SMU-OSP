from dataclasses import dataclass

from django import forms


@dataclass(frozen=True)
class UserListQuery:
    """검증된 사용자 목록 조회 조건."""

    start: int
    limit: int
    sort_by: str | None


class UserListQueryForm(forms.Form):
    """사용자 목록 query parameter를 검증한다."""

    start = forms.IntegerField(required=False, min_value=0)
    limit = forms.IntegerField(required=False, min_value=1, max_value=100)
    sort_by = forms.ChoiceField(
        required=False,
        choices=(
            ("commit", "commit"),
            ("star", "star"),
            ("pr", "pr"),
            ("issue", "issue"),
            ("score", "score"),
        ),
    )

    def to_query(self) -> UserListQuery:
        """검증 결과를 사용자 목록 조회 조건으로 변환한다.

        Returns:
            기본값이 보충된 사용자 목록 조회 조건.

        Raises:
            ValueError: 검증되지 않았거나 유효하지 않은 입력인 경우.
        """
        if not self.is_valid():
            raise ValueError("유효한 입력만 UserListQuery로 변환할 수 있습니다.")
        return UserListQuery(
            start=self.cleaned_data["start"] or 0,
            limit=self.cleaned_data["limit"] or 100,
            sort_by=self.cleaned_data["sort_by"] or None,
        )
