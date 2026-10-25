from datetime import datetime, timezone
import unittest

from scripts.public_e2e_schedule_watchdog import should_dispatch


class PublicE2EScheduleWatchdogTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 24, 7, 0, tzinfo=timezone.utc)
        self.main_sha = "a" * 40

    def run_record(
        self,
        *,
        sha=None,
        branch="main",
        status="completed",
        conclusion="success",
        created_at="2026-10-24T06:30:00Z",
    ):
        return {
            "head_branch": branch,
            "head_sha": sha or self.main_sha,
            "status": status,
            "conclusion": conclusion,
            "created_at": created_at,
        }

    def test_dispatches_when_no_main_run_exists(self):
        dispatch, _ = should_dispatch(
            self.main_sha,
            [self.run_record(branch="feature/example")],
            now=self.now,
        )
        self.assertTrue(dispatch)

    def test_does_not_duplicate_active_exact_main_run(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(status="in_progress")],
            now=self.now,
        )
        self.assertFalse(dispatch)
        self.assertIn("already queued or running", reason)

    def test_does_not_duplicate_exact_main_run_waiting_for_approval(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(status="waiting")],
            now=self.now,
        )
        self.assertFalse(dispatch)
        self.assertIn("already queued or running", reason)

    def test_does_not_duplicate_recent_completed_exact_main_run(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(created_at="2026-10-24T06:30:00Z")],
            now=self.now,
        )
        self.assertFalse(dispatch)
        self.assertIn("recent", reason)

    def test_dispatches_when_latest_run_targets_an_older_sha(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(sha="b" * 40, created_at="2026-10-24T06:59:00Z")],
            now=self.now,
        )
        self.assertTrue(dispatch)
        self.assertIn("stale for current main", reason)

    def test_dispatches_when_exact_main_run_is_older_than_threshold(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(created_at="2026-10-24T05:40:00Z")],
            now=self.now,
        )
        self.assertTrue(dispatch)
        self.assertIn("stale for current main", reason)

    def test_suppresses_repeat_failed_exact_main_run_while_render_is_behind(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(conclusion="failure", created_at="2026-10-24T05:00:00Z")],
            now=self.now,
            deployed_sha="b" * 40,
        )
        self.assertFalse(dispatch)
        self.assertIn("Render is still behind", reason)

    def test_suppresses_repeat_failed_exact_main_run_when_render_sha_is_unverified(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(conclusion="failure", created_at="2026-10-24T05:00:00Z")],
            now=self.now,
            deployed_sha=None,
        )
        self.assertFalse(dispatch)
        self.assertIn("unverified", reason)

    def test_suppresses_failed_exact_main_run_even_when_timestamp_is_invalid(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(conclusion="failure", created_at="not-a-timestamp")],
            now=self.now,
            deployed_sha="b" * 40,
        )
        self.assertFalse(dispatch)
        self.assertIn("Render is still behind", reason)

    def test_retries_stale_failed_run_after_render_reaches_current_main(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(conclusion="failure", created_at="2026-10-24T05:00:00Z")],
            now=self.now,
            deployed_sha=self.main_sha,
        )
        self.assertTrue(dispatch)
        self.assertIn("stale for current main", reason)

    def test_dispatches_when_failed_run_targets_old_sha(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(sha="b" * 40, conclusion="failure", created_at="2026-10-24T06:59:00Z")],
            now=self.now,
            deployed_sha="c" * 40,
        )
        self.assertTrue(dispatch)
        self.assertIn("stale for current main", reason)

    def test_dispatches_if_latest_timestamp_is_unverifiable(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(created_at="not-a-timestamp")],
            now=self.now,
        )
        self.assertTrue(dispatch)
        self.assertIn("invalid", reason)


if __name__ == "__main__":
    unittest.main()
