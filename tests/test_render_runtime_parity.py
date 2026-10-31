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

    def test_excluded_prefixes_stay_out_of_both_render_images(self) -> None:
        # The classifier intentionally excludes scripts/, tests/ and workflow
        # files from parity. Tie that assumption to the actual build inputs so
        # broad or unreviewed COPY/ADD instructions fail closed.
        root = Path(__file__).resolve().parents[1]
        excluded_prefixes = {".github", "tests", "scripts"}
        broad_sources = {".", "./", "*", "./*", "**", "./**"}
        allowed_sources = {
            "pyproject.toml",
            "README.md",
            "src",
            "webapp",
            "configs",
            "docs/RESEARCH_PROTOCOL.md",
            "docs/DATASETS.md",
        }

        for relative in ("webapp/community.Dockerfile", "webapp/Dockerfile"):
            dockerfile = root / relative
            for line_number, raw_line in enumerate(
                dockerfile.read_text(encoding="utf-8").splitlines(), start=1
            ):
                line = raw_line.split("#", 1)[0].strip()
                if not line:
                    continue
                tokens = line.split()
                if tokens[0].upper() not in {"COPY", "ADD"}:
                    continue
                # A continued instruction can hide additional source operands on
                # later lines. Fail closed rather than silently under-classifying
                # files that are excluded from runtime parity.
                if line.endswith("\\"):
                    self.fail(
                        f"{relative}:{line_number}: continued COPY/ADD instructions "
                        "must be reviewed before excluding non-runtime paths"
                    )
                operands = [token for token in tokens[1:] if not token.startswith("--")]
                if len(operands) < 2:
                    self.fail(f"{relative}:{line_number}: malformed COPY/ADD instruction")
                for source in operands[:-1]:
                    normalized = (
                        source.replace("\\", "/")
                        .strip("[]")
                        .strip(",")
                        .strip('"')
                        .strip("'")
                    )
                    if normalized in broad_sources:
                        self.fail(
                            f"{relative}:{line_number}: broad COPY/ADD source {source!r} "
                            "invalidates non-runtime path exclusions"
                        )
                    parts = [part for part in normalized.strip("/").split("/") if part]
                    if any(part in excluded_prefixes for part in parts):
                        self.fail(
                            f"{relative}:{line_number}: COPY/ADD source {source!r} "
                            "includes a path excluded from runtime parity"
                        )
                    if normalized not in allowed_sources:
                        self.fail(
                            f"{relative}:{line_number}: unreviewed COPY/ADD source {source!r}; "
                            "review the source explicitly before changing parity exclusions"
                        )

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
