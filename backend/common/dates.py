from datetime import date, timedelta

ONE_YEAR_RANKING_DAYS = 365
SIX_MONTH_RANKING_DAYS = 180


def ranking_period_boundary(period_end: date, days: int) -> date:
    """랭킹 집계 종료일에서 지정 일수 전의 경계를 반환한다."""
    return period_end - timedelta(days=days)
