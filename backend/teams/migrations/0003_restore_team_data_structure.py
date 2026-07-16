import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def table_columns(connection, table_name):
    with connection.cursor() as cursor:
        return {
            column.name
            for column in connection.introspection.get_table_description(
                cursor,
                table_name,
            )
        }


def restore_team_data_structure(apps, schema_editor):
    # The local database may still contain tables created by the previous
    # unmerged Team work. Add only schema elements that are actually missing.
    from teams.models import Team, TeamMember

    connection = schema_editor.connection
    tables = set(connection.introspection.table_names())
    team_table = Team._meta.db_table

    if team_table in tables:
        columns = table_columns(connection, team_table)
        for field_name in ("logo_url", "leader_name"):
            if field_name not in columns:
                schema_editor.add_field(Team, Team._meta.get_field(field_name))

    if TeamMember._meta.db_table not in tables:
        schema_editor.create_model(TeamMember)


class Migration(migrations.Migration):
    dependencies = [
        ("teams", "0002_remove_legacy_leader_name"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    restore_team_data_structure,
                    migrations.RunPython.noop,
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="team",
                    name="logo_url",
                    field=models.URLField(blank=True, max_length=500, null=True),
                ),
                migrations.AddField(
                    model_name="team",
                    name="leader_name",
                    field=models.CharField(default="", max_length=100),
                ),
                migrations.CreateModel(
                    name="TeamMember",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        ("created_at", models.DateTimeField(auto_now_add=True)),
                        ("updated_at", models.DateTimeField(auto_now=True)),
                        ("name", models.CharField(max_length=100)),
                        ("role", models.CharField(max_length=100)),
                        (
                            "github_id",
                            models.CharField(blank=True, max_length=100, null=True),
                        ),
                        ("email", models.EmailField(blank=True, max_length=254, null=True)),
                        (
                            "status",
                            models.CharField(
                                choices=[("ACTIVE", "Active"), ("INACTIVE", "Inactive")],
                                default="ACTIVE",
                                max_length=30,
                            ),
                        ),
                        ("joined_at", models.DateTimeField(auto_now_add=True)),
                        (
                            "team",
                            models.ForeignKey(
                                on_delete=django.db.models.deletion.CASCADE,
                                related_name="members",
                                to="teams.team",
                            ),
                        ),
                        (
                            "user",
                            models.ForeignKey(
                                blank=True,
                                null=True,
                                on_delete=django.db.models.deletion.SET_NULL,
                                related_name="team_memberships",
                                to=settings.AUTH_USER_MODEL,
                            ),
                        ),
                    ],
                    options={"abstract": False},
                ),
            ],
        ),
    ]
