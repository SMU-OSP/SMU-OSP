from datetime import date, datetime, timedelta

from django.conf import settings
from django.db import transaction

from .constants import TRENDING_REPOSITORY_LIMIT
from .github_client import (
    TrendingRepositoryCandidate,
    search_trending_repositories,
)
from .models import TrendingRepository, TrendingRepositorySelection
from .selectors import (
    has_successful_selection,
    list_recent_github_ids,
    list_repository_languages_by_usage,
)

COLLECTION_LANGUAGE_LIMIT = 5
SEARCH_PAGE_SIZE = 100
RETENTION_DAYS = 180
INITIAL_LANGUAGES = (
    "Python",
    "JavaScript",
    "TypeScript",
    "Java",
    "C++",
)


def _week_start(target: datetime) -> date:
    return target.date() - timedelta(days=target.weekday())


def _excluded_languages() -> set[str]:
    return {
        language.strip()
        for language in settings.TRENDING_EXCLUDED_LANGUAGES
        if language.strip()
    }


def list_collection_languages(
    *,
    excluded_languages: set[str],
) -> list[str]:
    """상위 Repository 언어를 우선하고 부족분을 초기 언어로 채운다."""
    excluded = {language.casefold() for language in excluded_languages}
    selected: list[str] = []
    selected_names: set[str] = set()
    languages = (
        *list_repository_languages_by_usage(),
        *INITIAL_LANGUAGES,
    )
    for language in languages:
        normalized = language.casefold()
        if normalized in excluded or normalized in selected_names:
            continue
        selected.append(language)
        selected_names.add(normalized)
        if len(selected) == COLLECTION_LANGUAGE_LIMIT:
            break
    return selected


def _select_candidates(
    candidates: list[TrendingRepositoryCandidate],
) -> list[TrendingRepositoryCandidate]:
    """후보를 Star 순으로 정렬해 최대 10개를 선정한다.

    중복 GitHub ID를 제거하며, Star가 같으면 full_name과 github_id
    오름차순으로 순서를 결정한다.
    """
    selected: list[TrendingRepositoryCandidate] = []
    selected_github_ids: set[int] = set()
    for candidate in sorted(
        candidates,
        key=lambda item: (-item.stars, item.full_name, item.github_id),
    ):
        if candidate.github_id in selected_github_ids:
            continue
        selected.append(candidate)
        selected_github_ids.add(candidate.github_id)
        if len(selected) == TRENDING_REPOSITORY_LIMIT:
            break
    return selected


def _collect_language_candidates(
    *,
    language: str,
    created_after: str,
    excluded_github_ids: set[int],
) -> list[TrendingRepositoryCandidate]:
    """한 언어에서 최근 노출되지 않은 후보를 최대 10개 수집한다.

    첫 페이지의 후보가 최근 노출 대상으로 제외되면 다음 페이지를
    조회한다. 유효 후보가 10개가 되거나 검색 결과가 끝나면 종료한다.
    """
    candidates: list[TrendingRepositoryCandidate] = []
    candidate_github_ids: set[int] = set()
    page = 1
    while len(candidates) < TRENDING_REPOSITORY_LIMIT:
        result = search_trending_repositories(
            language=language,
            created_after=created_after,
            page=page,
            per_page=SEARCH_PAGE_SIZE,
        )
        for candidate in result.repositories:
            if (
                candidate.github_id in excluded_github_ids
                or candidate.github_id in candidate_github_ids
            ):
                continue
            candidates.append(candidate)
            candidate_github_ids.add(candidate.github_id)
            if len(candidates) == TRENDING_REPOSITORY_LIMIT:
                break
        if not result.has_next:
            break
        page += 1
    return candidates


def _collect_selected_candidates(
    *,
    languages: list[str],
    created_after: str,
    excluded_github_ids: set[int],
) -> list[TrendingRepositoryCandidate]:
    """언어별 유효 후보를 모아 전체 Star 순 상위 10개를 반환한다."""
    candidates: list[TrendingRepositoryCandidate] = []
    for language in languages:
        candidates.extend(
            _collect_language_candidates(
                language=language,
                created_after=created_after,
                excluded_github_ids=excluded_github_ids,
            )
        )
    return _select_candidates(candidates)


def collect_trending_repositories(*, collected_at: datetime) -> int:
    """이번 주 트렌딩 Repository를 수집하고 정상 결과만 저장한다.

    최근 180일 동안 노출한 Repository를 제외해 최대 10개를 선정한다.
    이번 주 정상 결과가 이미 있으면 재수집하지 않는다. GitHub 호출은
    트랜잭션 밖에서 완료하며, 호출 하나라도 실패하면 기존 결과를 유지한다.

    Returns:
        새로 저장한 Repository 수. 이미 이번 주 수집이 끝났으면 0.

    Raises:
        GitHubSearchError: GitHub 검색 또는 응답 검증에 실패한 경우.
    """
    week_start = _week_start(collected_at)
    if has_successful_selection(week_start):
        return 0
    selected_after = collected_at - timedelta(days=RETENTION_DAYS)
    recent_github_ids = list_recent_github_ids(selected_after)
    languages = list_collection_languages(
        excluded_languages=_excluded_languages()
    )
    selected_candidates = _collect_selected_candidates(
        languages=languages,
        created_after=selected_after.date().isoformat(),
        excluded_github_ids=recent_github_ids,
    )

    with transaction.atomic():
        selection, created = (
            TrendingRepositorySelection.objects.get_or_create(
                week_start=week_start
            )
        )
        if not created:
            return 0
        TrendingRepositorySelection.objects.filter(
            created_at__lt=selected_after
        ).exclude(pk=selection.pk).delete()
        TrendingRepository.objects.bulk_create(
            [
                TrendingRepository(
                    selection=selection,
                    github_id=candidate.github_id,
                    full_name=candidate.full_name,
                    html_url=candidate.html_url,
                    description=candidate.description,
                    language=candidate.language,
                    stars=candidate.stars,
                    forks=candidate.forks,
                    position=position,
                )
                for position, candidate in enumerate(
                    selected_candidates,
                    start=1,
                )
            ]
        )
    return len(selected_candidates)
