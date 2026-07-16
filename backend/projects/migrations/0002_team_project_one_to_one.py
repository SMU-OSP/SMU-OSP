import django.db.models.deletion
from django.db import migrations, models


def deduplicate_project_names(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    seen_names = set()

    for project in Project.objects.all().order_by("pk"):
        base_name = (project.name or f"Project {project.pk}").strip()
        if not base_name:
            base_name = f"Project {project.pk}"

        candidate = base_name[:100]
        if candidate.lower() in seen_names:
            suffix = f"-{project.pk}"
            candidate = f"{base_name[:100 - len(suffix)]}{suffix}"

        counter = 2
        while candidate.lower() in seen_names:
            suffix = f"-{project.pk}-{counter}"
            candidate = f"{base_name[:100 - len(suffix)]}{suffix}"
            counter += 1

        seen_names.add(candidate.lower())
        if project.name != candidate:
            project.name = candidate
            project.save(update_fields=["name"])


def create_team_for_existing_projects(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    Team = apps.get_model("teams", "Team")

    for project in Project.objects.all().order_by("pk"):
        team = Team.objects.create(
            name=project.name,
            description=project.description,
        )
        project.team_id = team.pk
        project.team_name = project.name
        project.save(update_fields=["team_id", "team_name"])


class Migration(migrations.Migration):
    dependencies = [
        ("teams", "0001_initial"),
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(deduplicate_project_names, migrations.RunPython.noop),
        migrations.RunPython(create_team_for_existing_projects, migrations.RunPython.noop),
        migrations.RenameField(
            model_name="project",
            old_name="team_id",
            new_name="team",
        ),
        migrations.AlterField(
            model_name="project",
            name="team",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="project",
                to="teams.team",
            ),
        ),
        migrations.AlterField(
            model_name="project",
            name="name",
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.RemoveField(
            model_name="project",
            name="team_name",
        ),
    ]
