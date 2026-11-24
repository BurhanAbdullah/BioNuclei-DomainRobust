"""The frozen E4 checkpoint must come from its permanent release copy.

Actions artifact 12183110279 expired on 2026-11-18. Workflows must not fetch it
from the Actions artifact API any more, and the fetch script must keep both
pinned digests so provenance stays byte-identical.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E4_DIGEST = "89e66617e272d30ec46471c8403950c404c772780ad778dd6f0e992fc795df0d"
PACKAGE_DIGEST = "aef466d4d1a9c76d5378b519243641e7d160a5506aa94073fe760d130651a0f9"


def test_fetch_script_pins_both_digests():
    script = (ROOT / "scripts" / "fetch_frozen_e4.sh").read_text()
    assert E4_DIGEST in script and PACKAGE_DIGEST in script
    assert "sha256sum --check --strict" in script
    assert "evidence-package-40061151659" in script


def test_no_workflow_reads_the_expired_e4_artifact():
    # E6 fraction workflows resolve a fresh E4 artifact from the triggering run,
    # which is allowed. Only the pinned, expired artifact must not be fetched.
    offenders = []
    for workflow in (ROOT / ".github" / "workflows").glob("*.yml"):
        text = workflow.read_text()
        pinned = 'E4_ARTIFACT_ID: "12183110279"' in text or "'12183110279'" in text
        if "actions/artifacts/12183110279" in text or (pinned and "actions/artifacts/${E4_ARTIFACT_ID}" in text):
            offenders.append(workflow.name)
    assert not offenders, offenders


def test_e4_consumers_use_the_fetch_script():
    for name in ("e7_bbbc038_external.yml", "e6_finalize_verified.yml", "e6_e7_uncertainty_analysis.yml"):
        assert "scripts/fetch_frozen_e4.sh" in (ROOT / ".github" / "workflows" / name).read_text(), name
