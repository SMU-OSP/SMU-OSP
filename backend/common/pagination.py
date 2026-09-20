def pagination_detail(
    start: int,
    limit: int,
    count: int,
) -> dict[str, dict[str, int | bool]]:
    """페이지 조회 결과의 응답 메타데이터를 만든다.

    Args:
        start: 조회를 시작한 순번.
        limit: 요청한 최대 결과 수.
        count: 전체 결과 수.

    Returns:
        API 응답의 pagination 상세 정보.
    """
    total_pages = (count + limit - 1) // limit if count else 1
    return {
        "pagination": {
            "start": start,
            "limit": limit,
            "count": count,
            "currentPage": (start // limit) + 1,
            "totalPages": total_pages,
            "hasPrevious": start > 0,
            "hasNext": start + limit < count,
        }
    }
