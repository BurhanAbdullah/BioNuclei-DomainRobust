from __future__ import annotations

import fnmatch
from pathlib import Path
import unittest


from scripts.render_runtime_parity import is_non_runtime_path


class RenderRuntimeParityTests(unittest.TestCase):
    def test_render_build_inputs_remain_parity_gated(self) -> None:
        runtime_paths = (
            "webapp/community.py",
            "webapp/community_app.py",
            "webapp/community.Dockerfile",
            "webapp/Dockerfile",
            ".dockerignore",
            "webapp/Dockerfile.dockerignore",
            "webapp/community.Dockerfile.dockerignore",
            "src/bionuclei/inference.py",
            "configs/base_system.yaml",
            "pyproject.toml",
            "README.md",
            "render.yaml",
            "deploy/render-cpu-constraints.txt",
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
            "scripts/live_public_agent_e2e.py",
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
        self.assertFalse(is_non_runtime_path("scripts-extra/runtime.py"))

    def test_parity_helper_changes_trigger_main_e2e(self) -> None:
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github" / "workflows" / "live-public-agent-e2e.yml").read_text(encoding="utf-8")
        push_section = workflow.split("  push:\n", 1)[1].split("  pull_request:\n", 1)[0]
        self.assertIn('      - "scripts/render_runtime_parity.py"', push_section)

    def test_every_render_image_input_triggers_main_e2e(self) -> None:
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github" / "workflows" / "live-public-agent-e2e.yml").read_text(encoding="utf-8")
        push_section = workflow.split("  push:\n", 1)[1].split("  pull_request:\n", 1)[0]
        push_patterns = [
            line.strip().removeprefix("- ").strip().strip('"')
            for line in push_section.splitlines()
            if line.strip().startswith("- ")
        ]
        source_root = root / "src"
        source_inputs = tuple(
            path.relative_to(root).as_posix()
            for path in sorted(source_root.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
        )
        self.assertTrue(source_inputs, "Render image source tree must contain tracked source files")

        render_inputs = (
            "webapp/community.py",
            *source_inputs,
            "configs/base_system.yaml",
            "pyproject.toml",
            "README.md",
            "docs/RESEARCH_PROTOCOL.md",
            "docs/DATASETS.md",
            "render.yaml",
            "deploy/render-cpu-constraints.txt",
            ".dockerignore",
            "webapp/Dockerfile.dockerignore",
            "webapp/community.Dockerfile.dockerignore",
        )
        for path in render_inputs:
            with self.subTest(path=path):
                self.assertTrue(
                    any(fnmatch.fnmatchcase(path, pattern) for pattern in push_patterns),
                    f"{path} does not trigger the main-branch E2E parity gate",
                )

    def test_cpu_constraint_file_triggers_pr_harness(self) -> None:
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github" / "workflows" / "live-public-agent-e2e.yml").read_text(encoding="utf-8")
        pull_request_section = workflow.split("  pull_request:\n", 1)[1].split("\npermissions:\n", 1)[0]
        self.assertIn('      - "deploy/render-cpu-constraints.txt"', pull_request_section)

    def test_excluded_prefixes_stay_out_of_both_render_images(self) -> None:
        root = Path(__file__).resolve().parents[1]
        excluded_prefixes = {".github", "tests", "scripts"}
        broad_sources = {".", "./", "*", "./*", "**", "./**"}
        allowed_sources = {
            "pyproject.toml",
            "README.md",
            "src",
            "webapp",
            "configs",
            "deploy/render-cpu-constraints.txt",
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


if __name__ == "__main__":
    unittest.main()
