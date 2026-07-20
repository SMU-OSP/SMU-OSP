from django.db import connection
from django.test import TestCase


class TeamTableRemovalTests(TestCase):
    def test_legacy_team_tables_are_removed(self):
        table_names = connection.introspection.table_names()

        self.assertNotIn("teams_team", table_names)
        self.assertNotIn("teams_teammember", table_names)
