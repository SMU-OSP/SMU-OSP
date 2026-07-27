from urllib.parse import urlparse

from .models import Repository
from .tasks import enqueue_repository_refresh

REPOSITORY_ALREADY_LINKED_MESSAGE = (
    "이미 다른 프로젝트에 연결된 Repository입니다."
)
REPOSITORY_CHANGE_NOT_ALLOWED_MESSAGE = (
    "이미 등록된 Repository는 변경하거나 연결 해제할 수 없습니다."
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


def update_project_repository(project, repository_url):
    repository = getattr(project, "repository", None)
    if repository:
        if repository_url != repository.html_url:
            raise ValueError(REPOSITORY_CHANGE_NOT_ALLOWED_MESSAGE)
        return
    if not repository_url:
        return

    repository_name, full_name = _parse_repository_identity(repository_url)
    if Repository.objects.filter(full_name__iexact=full_name).exists():
        raise ValueError(REPOSITORY_ALREADY_LINKED_MESSAGE)

    repository = Repository.objects.create(
        project=project,
        name=repository_name,
        full_name=full_name,
        html_url=repository_url,
    )
    enqueue_repository_refresh(repository.pk)
