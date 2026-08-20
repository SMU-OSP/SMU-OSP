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


class RankingReportForm(forms.Form):
    """관리자 랭킹 조회 기간과 유형을 검증한다."""

    ranking_type = forms.ChoiceField(
        label="유형",
        choices=(
            ("users", "사용자"),
            ("projects", "프로젝트"),
        ),
    )
    period_start = forms.DateField(
        label="시작일",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    period_end = forms.DateField(
        label="종료일",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    def clean(self):
        """집계 시작일이 종료일보다 늦지 않은지 확인한다."""
        cleaned_data = super().clean()
        period_start = cleaned_data.get("period_start")
        period_end = cleaned_data.get("period_end")
        if period_start and period_end and period_start > period_end:
            self.add_error(
                "period_end",
                "종료일은 시작일과 같거나 이후여야 합니다.",
            )
        return cleaned_data
