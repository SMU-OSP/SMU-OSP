import django.db.models.deletion
from django.db import migrations, models
from django.utils import timezone


def table_has_column(schema_editor, table_name, column_name):
    with schema_editor.connection.cursor() as cursor:
        columns = schema_editor.connection.introspection.get_table_description(
            cursor,
            table_name,
        )
    return any(column.name == column_name for column in columns)


def create_team(Team, schema_editor, name, description):
    table_name = Team._meta.db_table
    if not table_has_column(schema_editor, table_name, "leader_name"):
        return Team.objects.create(
            name=name,
            description=description,
        ).pk

    quote = schema_editor.quote_name
    now = timezone.now()
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            (
                f"INSERT INTO {quote(table_name)} "
                f"({quote('created_at')}, {quote('updated_at')}, "
                f"{quote('name')}, {quote('description')}, {quote('leader_name')}) "
                "VALUES (%s, %s, %s, %s, %s)"
            ),
            [now, now, name, description, ""],
        )
        return cursor.lastrowid


def create_team_for_existing_projects(apps, schema_editor):
    Project = apps.get_model("projects", "Project")
    Team = apps.get_model("teams", "Team")

    for project in Project.objects.all().order_by("pk"):
        base_name = (project.name or project.team_name or f"Project {project.pk}")[:100]
        team_name = base_name
        if Team.objects.filter(name=team_name).exists():
            suffix = f"-{project.pk}"
            team_name = f"{base_name[:100 - len(suffix)]}{suffix}"

        team_id = create_team(
            Team,
            schema_editor,
            team_name,
            project.description,
        )
        project.team_id = team_id
        project.team_name = team_name
        project.save(update_fields=["team_id", "team_name"])


class Migration(migrations.Migration):
    dependencies = [
        ("teams", "0001_initial"),
        ("projects", "0001_initial"),
    ]

    operations = [
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
