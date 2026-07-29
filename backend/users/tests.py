from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase


class UserSignalTests(TestCase):
    @patch("users.signals.initial_process.delay")
    def test_initial_process_is_queued_after_user_commit(self, delay):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            get_user_model().objects.create_user(
                username="celery-test",
                github_email="celery-test@example.com",
                name="테스트 사용자",
                student_id=1,
                major="IT공학",
            )
            delay.assert_not_called()

        self.assertEqual(len(callbacks), 1)
        delay.assert_called_once_with("celery-test")
