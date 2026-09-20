import json
from pathlib import Path


def seed_project_languages(**kwargs):
    try:
        project_language = kwargs["apps"].get_model(
            "projects",
            "ProjectLanguage",
        )
    except LookupError:
        return

    data_path = Path(__file__).with_name("data") / "project_languages.json"
    names = json.loads(data_path.read_text())["languages"]
    project_language.objects.bulk_create(
        (project_language(name=name) for name in names),
        ignore_conflicts=True,
    )
