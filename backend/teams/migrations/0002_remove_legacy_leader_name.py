from django.db import migrations


def table_has_column(schema_editor, table_name, column_name):
    with schema_editor.connection.cursor() as cursor:
        columns = schema_editor.connection.introspection.get_table_description(
            cursor,
            table_name,
        )
    return any(column.name == column_name for column in columns)


def remove_legacy_leader_name(apps, schema_editor):
    Team = apps.get_model("teams", "Team")
    table_name = Team._meta.db_table

    if not table_has_column(schema_editor, table_name, "leader_name"):
        return

    schema_editor.execute(
        f"ALTER TABLE {schema_editor.quote_name(table_name)} "
        f"DROP COLUMN {schema_editor.quote_name('leader_name')}"
    )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("teams", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(remove_legacy_leader_name, migrations.RunPython.noop),
    ]
