from urllib.parse import urlparse

from .models import Repository
from .tasks import enqueue_repository_refresh

REPOSITORY_ALREADY_LINKED_MESSAGE = (
    "이미 다른 프로젝트에 연결된 Repository입니다."
)


def _parse_repository_identity(repository_url):
    parsed = urlparse(repository_url)
    path_parts = [part for part in parsed.path.split("/") if part]
    repository_name = (
        path_parts[-1].removesuffix(".git")
        if path_parts
        else parsed.hostname or "repository"
    )
    full_name = (
        "/".join(path_parts[-2:]).removesuffix(".git")
        if len(path_parts) >= 2
        else repository_name
    )
    return repository_name[:150], full_name[:300]


def _validate_repository_availability(full_name, repository=None):
    repositories = Repository.objects.filter(full_name__iexact=full_name)
    if repository:
        repositories = repositories.exclude(pk=repository.pk)
    if repositories.exists():
        raise ValueError(REPOSITORY_ALREADY_LINKED_MESSAGE)


def update_project_repository(project, repository_url):
    repository = getattr(project, "repository", None)

    if not repository_url:
        if repository:
            repository.delete()
        return

    if repository and repository.html_url == repository_url:
        return

    repository_name, full_name = _parse_repository_identity(repository_url)
    _validate_repository_availability(full_name, repository)
    if not repository:
        repository = Repository.objects.create(
            project=project,
            name=repository_name,
            full_name=full_name,
            html_url=repository_url,
        )
        enqueue_repository_refresh(repository.pk)
        return

    repository.github_id = None
    repository.name = repository_name
    repository.full_name = full_name
    repository.description = None
    repository.stars = 0
    repository.forks = 0
    repository.language = None
    repository.topics = []
    repository.html_url = repository_url
    repository.github_updated_at = None
    repository.fetched_at = None
    repository.refresh_status = None
    repository.last_error_code = None
    repository.save()
    enqueue_repository_refresh(repository.pk)
