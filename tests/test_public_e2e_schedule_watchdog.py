from datetime import datetime, timezone
import json
import os
import unittest
from unittest.mock import patch

from scripts.public_e2e_schedule_watchdog import (
    EXPECTED_CHECKPOINT_SHA256,
    _api_request,
    _deployed_runtime_sha,
    _github_server_time,
    main,
    should_dispatch,
)


class _HealthResponse:
    status = 200

    def __init__(self, payload):
        self.raw = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, size=-1):
        return self.raw if size < 0 else self.raw[:size]


class _APIResponse:
    def __init__(self, payload, date_header=None):
        self.raw = json.dumps(payload).encode("utf-8")
        self.headers = {"Date": date_header} if date_header else {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, size=-1):
        return self.raw if size < 0 else self.raw[:size]


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

    def _healthy_runtime(self, **overrides):
        return {
            "status": "ok",
            "render_git_branch": "main",
            "render_git_commit": self.main_sha,
            "checkpoint_available": True,
            "checkpoint_verified": True,
            "checkpoint_sha256": EXPECTED_CHECKPOINT_SHA256,
            **overrides,
        }

    def test_deployed_runtime_sha_requires_pinned_checkpoint_identity(self):
        with patch(
            "scripts.public_e2e_schedule_watchdog.urlopen",
            return_value=_HealthResponse(self._healthy_runtime()),
        ):
            self.assertEqual(_deployed_runtime_sha(), self.main_sha)

    def test_deployed_runtime_sha_fails_closed_on_unverified_checkpoint(self):
        invalid_health = (
            {"status": "degraded"},
            {"checkpoint_available": False},
            {"checkpoint_verified": False},
            {"checkpoint_sha256": "0" * 64},
            {"checkpoint_sha256": None},
        )
        for overrides in invalid_health:
            with self.subTest(overrides=overrides):
                with patch(
                    "scripts.public_e2e_schedule_watchdog.urlopen",
                    return_value=_HealthResponse(self._healthy_runtime(**overrides)),
                ):
                    self.assertIsNone(_deployed_runtime_sha())

    def test_dispatches_when_no_main_run_exists_and_render_is_current(self):
        dispatch, _ = should_dispatch(
            self.main_sha,
            [self.run_record(branch="feature/example")],
            now=self.now,
            deployed_sha=self.main_sha,
        )
        self.assertTrue(dispatch)

    def test_suppresses_when_no_main_run_exists_and_render_is_behind(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(branch="feature/example")],
            now=self.now,
            deployed_sha="b" * 40,
        )
        self.assertFalse(dispatch)
        self.assertIn("Render is still behind", reason)

    def test_suppresses_when_no_main_run_exists_and_render_is_unverified(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(branch="feature/example")],
            now=self.now,
            deployed_sha=None,
        )
        self.assertFalse(dispatch)
        self.assertIn("unverified", reason)

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

    def test_dispatches_when_latest_run_targets_an_older_sha_and_render_is_current(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(sha="b" * 40, created_at="2026-10-24T06:59:00Z")],
            now=self.now,
            deployed_sha=self.main_sha,
        )
        self.assertTrue(dispatch)
        self.assertIn("stale for current main", reason)

    def test_suppresses_when_latest_run_targets_an_older_sha_and_render_is_behind(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(sha="b" * 40, created_at="2026-10-24T06:59:00Z")],
            now=self.now,
            deployed_sha="b" * 40,
        )
        self.assertFalse(dispatch)
        self.assertIn("Render is still behind", reason)

    def test_suppresses_when_latest_run_targets_an_older_sha_and_render_is_unverified(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(sha="b" * 40, created_at="2026-10-24T06:59:00Z")],
            now=self.now,
            deployed_sha=None,
        )
        self.assertFalse(dispatch)
        self.assertIn("unverified", reason)

    def test_dispatches_when_exact_main_run_is_older_than_threshold(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(created_at="2026-10-24T05:40:00Z")],
            now=self.now,
            deployed_sha=self.main_sha,
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

    def test_dispatches_when_failed_run_targets_old_sha_and_render_is_current(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(sha="b" * 40, conclusion="failure", created_at="2026-10-24T06:59:00Z")],
            now=self.now,
            deployed_sha=self.main_sha,
        )
        self.assertTrue(dispatch)
        self.assertIn("stale for current main", reason)

    def test_dispatches_if_latest_timestamp_is_unverifiable_and_render_is_current(self):
        dispatch, reason = should_dispatch(
            self.main_sha,
            [self.run_record(created_at="not-a-timestamp")],
            now=self.now,
            deployed_sha=self.main_sha,
        )
        self.assertTrue(dispatch)
        self.assertIn("invalid", reason)


    def test_github_server_time_parses_http_date_and_fails_closed(self):
        self.assertEqual(
            _github_server_time("Sun, 01 Nov 2026 09:14:25 GMT"),
            datetime(2026, 11, 1, 9, 14, 25, tzinfo=timezone.utc),
        )
        self.assertIsNone(_github_server_time(None))
        self.assertIsNone(_github_server_time("not-a-date"))

    def test_api_request_returns_authoritative_server_time(self):
        response = _APIResponse(
            {"sha": self.main_sha},
            "Sun, 01 Nov 2026 09:14:25 GMT",
        )
        with patch(
            "scripts.public_e2e_schedule_watchdog.urlopen",
            return_value=response,
        ):
            payload, server_now = _api_request(
                "owner/repo",
                "commits/main",
                "test-token",
                include_server_time=True,
            )
        self.assertEqual(payload, {"sha": self.main_sha})
        self.assertEqual(
            server_now,
            datetime(2026, 11, 1, 9, 14, 25, tzinfo=timezone.utc),
        )

    def test_main_uses_github_server_time_for_freshness_decisions(self):
        server_now = datetime(2026, 11, 1, 9, 14, 25, tzinfo=timezone.utc)
        runs = [self.run_record(created_at="2026-11-01T07:39:00Z")]
        with (
            patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo", "GH_TOKEN": "test-token"}),
            patch(
                "scripts.public_e2e_schedule_watchdog._api_request",
                side_effect=[{"sha": self.main_sha}, ({"workflow_runs": runs}, server_now)],
            ),
            patch(
                "scripts.public_e2e_schedule_watchdog._deployed_runtime_sha",
                return_value=self.main_sha,
            ),
            patch(
                "scripts.public_e2e_schedule_watchdog.should_dispatch",
                return_value=(False, "test suppression"),
            ) as decision,
        ):
            self.assertEqual(main(), 0)
        decision.assert_called_once_with(
            self.main_sha,
            runs,
            now=server_now,
            deployed_sha=self.main_sha,
        )

    def test_main_fails_closed_when_github_server_time_is_missing(self):
        with (
            patch.dict(os.environ, {"GITHUB_REPOSITORY": "owner/repo", "GH_TOKEN": "test-token"}),
            patch(
                "scripts.public_e2e_schedule_watchdog._api_request",
                side_effect=[{"sha": self.main_sha}, ({"workflow_runs": []}, None)],
            ),
            patch("scripts.public_e2e_schedule_watchdog._deployed_runtime_sha") as deployed,
            patch("scripts.public_e2e_schedule_watchdog.should_dispatch") as decision,
        ):
            self.assertEqual(main(), 0)
        deployed.assert_not_called()
        decision.assert_not_called()


    def test_main_never_dispatches_when_render_is_stale_or_unverified(self):
        server_now = datetime(2026, 11, 1, 9, 14, 25, tzinfo=timezone.utc)
        runs = [
            self.run_record(
                sha="b" * 40,
                created_at="2026-11-01T07:39:00Z",
            )
        ]
        for deployed_sha in (None, "b" * 40):
            with self.subTest(deployed_sha=deployed_sha):
                with (
                    patch.dict(
                        os.environ,
                        {"GITHUB_REPOSITORY": "owner/repo", "GH_TOKEN": "test-token"},
                    ),
                    patch(
                        "scripts.public_e2e_schedule_watchdog._api_request",
                        side_effect=[
                            {"sha": self.main_sha},
                            ({"workflow_runs": runs}, server_now),
                        ],
                    ) as api_request,
                    patch(
                        "scripts.public_e2e_schedule_watchdog._deployed_runtime_sha",
                        return_value=deployed_sha,
                    ),
                ):
                    self.assertEqual(main(), 0)

                self.assertEqual(api_request.call_count, 2)
                self.assertFalse(
                    any(
                        len(call.args) > 1 and str(call.args[1]).endswith("/dispatches")
                        for call in api_request.call_args_list
                    )
                )



if __name__ == "__main__":
    unittest.main()
