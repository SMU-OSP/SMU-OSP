from dataclasses import dataclass

from django import forms


@dataclass(frozen=True)
class ProjectRankingQuery:
    """검증된 프로젝트 랭킹 페이지 조회 조건."""

    start: int
    limit: int


class ProjectRankingQueryForm(forms.Form):
    """프로젝트 랭킹 페이지 query parameter를 검증한다."""

    start = forms.IntegerField(required=False, min_value=0)
    limit = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=100,
    )

    def to_query(self) -> ProjectRankingQuery:
        """검증 결과를 랭킹 조회 조건으로 변환한다.

        Returns:
            기본값이 보충된 랭킹 조회 조건.

        Raises:
            ValueError: 검증되지 않았거나 유효하지 않은 입력인 경우.
        """
        if not self.is_valid():
            raise ValueError(
                "유효한 입력만 ProjectRankingQuery로 변환할 수 있습니다."
            )
        return ProjectRankingQuery(
            start=self.cleaned_data["start"] or 0,
            limit=self.cleaned_data["limit"] or 100,
        )
