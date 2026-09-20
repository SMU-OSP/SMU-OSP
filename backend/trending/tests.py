from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings

from projects.models import Project, Repository, RepositoryLanguage

from .github_client import (
    GitHubSearchError,
    TrendingRepositoryCandidate,
    TrendingRepositorySearchPage,
    search_trending_repositories,
)
from .models import TrendingRepository, TrendingRepositorySelection
from .services import (
    INITIAL_LANGUAGES,
    collect_trending_repositories,
    list_collection_languages,
)


def _candidate(
    github_id: int,
    *,
    language: str = "Python",
    stars: int | None = None,
) -> TrendingRepositoryCandidate:
    return TrendingRepositoryCandidate(
        github_id=github_id,
        full_name=f"owner/repository-{github_id}",
        html_url=f"https://github.com/owner/repository-{github_id}",
        description=f"Repository {github_id}",
        language=language,
        stars=stars if stars is not None else 2000 - github_id,
        forks=github_id,
    )


class TrendingGitHubClientTests(TestCase):
    @patch("trending.github_client.requests.get")
    def test_search_quotes_language_and_uses_confirmed_filters(
        self, request_get
    ):
        response = request_get.return_value
        response.status_code = 200
        response.json.return_value = {
            "total_count": 0,
            "incomplete_results": False,
            "items": [],
        }

        search_trending_repositories(
            language="Jupyter Notebook",
            created_after="2026-02-19",
            page=1,
            per_page=10,
        )

        params = request_get.call_args.kwargs["params"]
        self.assertEqual(
            params["q"],
            "created:>=2026-02-19 stars:>=1000 "
            'language:"Jupyter Notebook" is:public',
        )
        self.assertEqual(params["sort"], "stars")
        self.assertEqual(params["order"], "desc")

    @patch("trending.github_client.requests.get")
    def test_search_rejects_incomplete_results(self, request_get):
        response = request_get.return_value
        response.status_code = 200
        response.json.return_value = {
            "total_count": 1,
            "incomplete_results": True,
            "items": [],
        }

        with self.assertRaises(GitHubSearchError):
            search_trending_repositories(
                language="Python",
                created_after="2026-02-19",
                page=1,
                per_page=10,
            )

    @patch("trending.github_client.requests.get")
    def test_search_rejects_invalid_repository_items(self, request_get):
        response = request_get.return_value
        response.status_code = 200
        response.json.return_value = {
            "total_count": 1,
            "incomplete_results": False,
            "items": [{"id": "invalid"}],
        }

        with self.assertRaises(GitHubSearchError):
            search_trending_repositories(
                language="Python",
                created_after="2026-02-19",
                page=1,
                per_page=10,
            )

    def test_candidate_rejects_invalid_numeric_fields(self):
        valid_data = {
            "id": 1,
            "full_name": "owner/repository",
            "html_url": "https://github.com/owner/repository",
            "description": None,
            "language": "Python",
            "stargazers_count": 1000,
            "forks_count": 10,
        }
        invalid_values = (
            ("id", True),
            ("stargazers_count", True),
            ("forks_count", True),
            ("stargazers_count", -1),
            ("forks_count", -1),
        )

        for field, value in invalid_values:
            with (
                self.subTest(field=field, value=value),
                self.assertRaises(GitHubSearchError),
            ):
                TrendingRepositoryCandidate.from_data(
                    {**valid_data, field: value},
                    requested_language="Python",
                )

    def test_candidate_uses_requested_language_when_language_is_null(self):
        candidate = TrendingRepositoryCandidate.from_data(
            {
                "id": 1,
                "full_name": "owner/repository",
                "html_url": "https://github.com/owner/repository",
                "description": None,
                "language": None,
                "stargazers_count": 1000,
                "forks_count": 10,
            },
            requested_language="Jupyter Notebook",
        )

        self.assertEqual(candidate.language, "Jupyter Notebook")

    @patch("trending.github_client.requests.get")
    def test_search_rejects_http_error(self, request_get):
        request_get.return_value.status_code = 500

        with self.assertRaises(GitHubSearchError):
            search_trending_repositories(
                language="Python",
                created_after="2026-02-19",
                page=1,
                per_page=10,
            )


@override_settings(TRENDING_EXCLUDED_LANGUAGES=[])
class TrendingServiceTests(TestCase):
    def setUp(self):
        self.collected_at = datetime(
            2026,
            8,
            17,
            tzinfo=ZoneInfo("Asia/Seoul"),
        )

    def test_initial_languages_are_used_before_five_languages_exist(self):
        self.assertEqual(
            list_collection_languages(excluded_languages=set()),
            list(INITIAL_LANGUAGES),
        )

    def test_repository_languages_are_ranked_by_total_bytes(self):
        project = Project.objects.create(name="Project", description="Test")
        repository = Repository.objects.create(
            project=project,
            github_id=1,
            name="repository",
            full_name="owner/repository",
            html_url="https://github.com/owner/repository",
        )
        for index, language in enumerate(
            ("Python", "Java", "Go", "Rust", "Ruby", "PHP"),
            start=1,
        ):
            RepositoryLanguage.objects.create(
                repository=repository,
                language=language,
                bytes=index * 100,
            )

        languages = list_collection_languages(
            excluded_languages={"php"},
        )

        self.assertEqual(languages, ["Ruby", "Rust", "Go", "Java", "Python"])

    def test_repository_languages_are_completed_with_initial_languages(self):
        project = Project.objects.create(name="Project", description="Test")
        repository = Repository.objects.create(
            project=project,
            github_id=1,
            name="repository",
            full_name="owner/repository",
            html_url="https://github.com/owner/repository",
        )
        RepositoryLanguage.objects.create(
            repository=repository,
            language="Go",
            bytes=200,
        )
        RepositoryLanguage.objects.create(
            repository=repository,
            language="Python",
            bytes=100,
        )

        languages = list_collection_languages(excluded_languages=set())

        self.assertEqual(
            languages,
            ["Go", "Python", "JavaScript", "TypeScript", "Java"],
        )

    @patch("trending.services.list_collection_languages")
    @patch("trending.services.search_trending_repositories")
    def test_collection_saves_one_week_only_once(
        self,
        search_repositories,
        list_languages,
    ):
        list_languages.return_value = ["Python", "JavaScript"]
        search_repositories.side_effect = [
            TrendingRepositorySearchPage(
                repositories=tuple(_candidate(index) for index in range(1, 6)),
                has_next=False,
            ),
            TrendingRepositorySearchPage(
                repositories=tuple(
                    _candidate(index, language="JavaScript")
                    for index in range(6, 11)
                ),
                has_next=False,
            ),
        ]

        first_count = collect_trending_repositories(
            collected_at=self.collected_at
        )
        second_count = collect_trending_repositories(
            collected_at=self.collected_at + timedelta(days=1)
        )

        self.assertEqual(first_count, 10)
        self.assertEqual(second_count, 0)
        self.assertEqual(TrendingRepository.objects.count(), 10)
        self.assertEqual(TrendingRepositorySelection.objects.count(), 1)
        self.assertEqual(search_repositories.call_count, 2)

    @patch("trending.services.list_collection_languages")
    @patch("trending.services.search_trending_repositories")
    def test_collection_orders_candidates_by_stars_across_languages(
        self,
        search_repositories,
        list_languages,
    ):
        list_languages.return_value = ["Python", "JavaScript"]
        search_repositories.side_effect = [
            TrendingRepositorySearchPage(
                repositories=(
                    _candidate(1, stars=1500),
                    _candidate(2, stars=3000),
                ),
                has_next=False,
            ),
            TrendingRepositorySearchPage(
                repositories=(
                    _candidate(3, language="JavaScript", stars=2500),
                ),
                has_next=False,
            ),
        ]

        collect_trending_repositories(collected_at=self.collected_at)

        self.assertEqual(
            list(
                TrendingRepository.objects.order_by(
                    "position",
                    "github_id",
                ).values_list("github_id", "position")
            ),
            [(2, 1), (3, 2), (1, 3)],
        )

    @patch("trending.services.list_recent_github_ids")
    @patch("trending.services.list_collection_languages")
    @patch("trending.services.search_trending_repositories")
    def test_collection_reads_next_page_after_recent_candidates(
        self,
        search_repositories,
        list_languages,
        list_recent_ids,
    ):
        list_languages.return_value = ["Python", "JavaScript"]
        list_recent_ids.return_value = set(range(1, 11))

        def search_side_effect(*, language, page, **_kwargs):
            if language == "Python" and page == 1:
                return TrendingRepositorySearchPage(
                    repositories=tuple(
                        _candidate(index, stars=5000 - index)
                        for index in range(1, 11)
                    ),
                    has_next=True,
                )
            if language == "Python" and page == 2:
                return TrendingRepositorySearchPage(
                    repositories=(_candidate(11, stars=3000),),
                    has_next=False,
                )
            return TrendingRepositorySearchPage(
                repositories=tuple(
                    _candidate(
                        index,
                        language="JavaScript",
                        stars=2500 - index,
                    )
                    for index in range(20, 30)
                ),
                has_next=False,
            )

        search_repositories.side_effect = search_side_effect

        collect_trending_repositories(collected_at=self.collected_at)

        self.assertEqual(
            list(
                TrendingRepository.objects.order_by("position").values_list(
                    "github_id",
                    flat=True,
                )
            ),
            [11, *range(20, 29)],
        )
        search_repositories.assert_any_call(
            language="Python",
            created_after="2026-02-18",
            page=2,
            per_page=100,
        )

    @patch("trending.services.list_collection_languages")
    @patch("trending.services.search_trending_repositories")
    def test_partial_github_failure_keeps_previous_results(
        self,
        search_repositories,
        list_languages,
    ):
        previous_selection = TrendingRepositorySelection.objects.create(
            week_start=self.collected_at.date() - timedelta(days=7)
        )
        TrendingRepository.objects.create(
            selection=previous_selection,
            github_id=100,
            full_name="owner/previous",
            html_url="https://github.com/owner/previous",
            description="Previous result",
            language="Python",
            stars=3000,
            forks=10,
            position=1,
        )
        list_languages.return_value = ["Python", "JavaScript"]
        search_repositories.side_effect = [
            TrendingRepositorySearchPage(
                repositories=(_candidate(1),),
                has_next=False,
            ),
            GitHubSearchError("failed"),
        ]

        with self.assertRaises(GitHubSearchError):
            collect_trending_repositories(collected_at=self.collected_at)

        self.assertEqual(TrendingRepositorySelection.objects.count(), 1)
        self.assertEqual(
            list(
                TrendingRepository.objects.values_list(
                    "github_id",
                    flat=True,
                )
            ),
            [100],
        )

    @patch("trending.services.list_collection_languages")
    @patch("trending.services.search_trending_repositories")
    def test_collection_deletes_only_expired_selections(
        self,
        search_repositories,
        list_languages,
    ):
        expired_selection = TrendingRepositorySelection.objects.create(
            week_start=self.collected_at.date() - timedelta(days=189)
        )
        recent_selection = TrendingRepositorySelection.objects.create(
            week_start=self.collected_at.date() - timedelta(days=7)
        )
        selected_after = self.collected_at - timedelta(days=180)
        TrendingRepositorySelection.objects.filter(
            pk=expired_selection.pk
        ).update(created_at=selected_after - timedelta(seconds=1))
        TrendingRepositorySelection.objects.filter(
            pk=recent_selection.pk
        ).update(created_at=selected_after)
        list_languages.return_value = ["Python"]
        search_repositories.return_value = TrendingRepositorySearchPage(
            repositories=(),
            has_next=False,
        )

        collect_trending_repositories(collected_at=self.collected_at)

        self.assertFalse(
            TrendingRepositorySelection.objects.filter(
                pk=expired_selection.pk
            ).exists()
        )
        self.assertTrue(
            TrendingRepositorySelection.objects.filter(
                pk=recent_selection.pk
            ).exists()
        )


class TrendingApiTests(TestCase):
    def test_latest_ten_repositories_are_returned_in_selection_order(self):
        selection = TrendingRepositorySelection.objects.create(
            week_start=datetime(2026, 8, 17).date()
        )
        TrendingRepository.objects.bulk_create(
            [
                TrendingRepository(
                    selection=selection,
                    github_id=index,
                    full_name=f"owner/repository-{index}",
                    html_url=f"https://github.com/owner/repository-{index}",
                    description=None,
                    language="Python",
                    stars=2000 - index,
                    forks=index,
                    position=index,
                )
                for index in range(1, 12)
            ]
        )

        response = self.client.get("/api/v1/trending/repositories")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "SUCCESS")
        self.assertEqual(len(body["data"]), 10)
        self.assertEqual(body["data"][0]["githubId"], 1)
        self.assertEqual(body["data"][-1]["githubId"], 10)

    def test_only_repositories_from_latest_selection_are_returned(self):
        previous_selection = TrendingRepositorySelection.objects.create(
            week_start=datetime(2026, 8, 10).date()
        )
        latest_selection = TrendingRepositorySelection.objects.create(
            week_start=datetime(2026, 8, 17).date()
        )
        TrendingRepository.objects.create(
            selection=previous_selection,
            github_id=1,
            full_name="owner/previous",
            html_url="https://github.com/owner/previous",
            description=None,
            language="Python",
            stars=3000,
            forks=100,
            position=1,
        )
        TrendingRepository.objects.create(
            selection=latest_selection,
            github_id=2,
            full_name="owner/latest",
            html_url="https://github.com/owner/latest",
            description=None,
            language="Python",
            stars=2000,
            forks=50,
            position=1,
        )

        response = self.client.get("/api/v1/trending/repositories")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["githubId"] for item in response.json()["data"]],
            [2],
        )
