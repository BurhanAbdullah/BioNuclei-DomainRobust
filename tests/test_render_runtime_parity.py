from __future__ import annotations

from pathlib import Path
import unittest

import yaml

from scripts.render_runtime_parity import is_non_runtime_path


class RenderRuntimeParityTests(unittest.TestCase):
    def test_render_build_inputs_remain_parity_gated(self) -> None:
        runtime_paths = (
            "webapp/community.py",
            "webapp/community_app.py",
            "webapp/community.Dockerfile",
            "webapp/Dockerfile",
            "src/bionuclei/inference.py",
            "configs/base_system.yaml",
            "pyproject.toml",
            "README.md",
            "render.yaml",
            "docs/RESEARCH_PROTOCOL.md",
            "docs/DATASETS.md",
        )
        for path in runtime_paths:
            with self.subTest(path=path):
                self.assertFalse(is_non_runtime_path(path), path)

    def test_paths_not_copied_into_render_images_are_excluded(self) -> None:
        non_runtime_paths = (
            ".github/workflows/live-public-agent-e2e.yml",
            "tests/test_community_service.py",
            "scripts/aggregate_e6_fraction_evidence.py",
            "scripts/download_aitslab_bioimaging1.py",
            "scripts/public_e2e_schedule_watchdog.py",
            "docs/ANALYZER_WORKER_ARCHITECTURE.md",
            "docs/bionuclei-app.html",
            "CHANGELOG.md",
            "LICENSE",
        )
        for path in non_runtime_paths:
            with self.subTest(path=path):
                self.assertTrue(is_non_runtime_path(path), path)

    def test_unknown_root_paths_fail_closed(self) -> None:
        self.assertFalse(is_non_runtime_path("runtime-config.toml"))


    def test_public_upload_job_is_restricted_to_main_ref(self) -> None:
        root = Path(__file__).resolve().parents[1]
        workflow = yaml.load(
            (root / ".github" / "workflows" / "live-public-agent-e2e.yml").read_text(encoding="utf-8"),
            Loader=yaml.BaseLoader,
        )
        self.assertEqual(
            workflow["jobs"]["public-upload-to-agent"]["if"],
            "github.ref == 'refs/heads/main'",
        )

if __name__ == "__main__":
    unittest.main()
